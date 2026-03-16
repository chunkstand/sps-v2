"""M003 / S03 integration tests: Contradiction artifacts and advancement blocking.

Proves all three S03 scenarios against real Postgres (no Temporal worker needed).
The contradiction guard lives in `apply_state_transition`, a plain DB activity callable
as a regular Python function in tests.

Three test scenarios:

  1. Blocking contradiction denies advancement:
       - seed case + ReviewDecision (so denial is from contradiction, not missing review)
       - POST create blocking contradiction → 201
       - call apply_state_transition → DeniedStateTransitionResult
         event_type=CONTRADICTION_ADVANCE_DENIED, guard_assertion_id=INV-SPS-CONTRA-001,
         normalized_business_invariants=["INV-003"]

  2. Resolve allows advancement:
       - same setup as (1)
       - POST resolve → 200
       - call apply_state_transition with fresh request_id → AppliedStateTransitionResult
         event_type=CASE_STATE_CHANGED

  3. Non-blocking contradiction is transparent:
       - seed case; POST create contradiction with blocking_effect=false
       - call apply_state_transition without valid required_review_id
       - assert DeniedStateTransitionResult with event_type=APPROVAL_GATE_DENIED
         (proves non-blocking contradictions are invisible to the contradiction guard)

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.
Pattern: mirrors m003_s02 (real Postgres, no Temporal worker needed).

## Observability Impact

Signals documented by these tests:
  - contradiction_api.create  contradiction_id=... case_id=... blocking_effect=...
  - contradiction_api.resolve  contradiction_id=... case_id=...
  - apply_state_transition emits event_type=CONTRADICTION_ADVANCE_DENIED to case_transition_ledger
    with guard_assertion_id=INV-SPS-CONTRA-001 and normalized_business_invariants=["INV-003"]

Diagnostic inspection:
  - SELECT contradiction_id, resolution_status, resolved_at FROM contradiction_artifacts;
  - SELECT event_type, payload FROM case_transition_ledger ORDER BY occurred_at;
  - GET /api/v1/contradictions/{id} — read-only endpoint (returns full artifact)

Failure state visibility:
  - event_type=CONTRADICTION_ADVANCE_DENIED persisted to case_transition_ledger.payload
    with guard_assertion_id + normalized_business_invariants for cross-system correlation
  - DeniedStateTransitionResult fields confirm exact denial cause without DB access
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import time
import uuid

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import ContradictionArtifact, PermitCase, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import apply_state_transition
from sps.workflows.permit_case.contracts import (
    ActorType,
    AppliedStateTransitionResult,
    CaseState,
    DeniedStateTransitionResult,
    StateTransitionRequest,
)

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers (inlined — self-contained, no coupling to other test modules)
# ---------------------------------------------------------------------------


def _wait_for_postgres_ready(timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    engine = get_engine()

    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            time.sleep(0.5)

    raise RuntimeError(
        f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})"
    )


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _reset_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE case_transition_ledger, review_decisions,"
                " contradiction_artifacts, permit_cases CASCADE"
            )
        )


def _seed_permit_case(case_id: str) -> None:
    """Insert a minimal PermitCase row so FK constraints are satisfied.

    State is REVIEW_PENDING — the starting state for all advancement tests.
    """
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = PermitCase(
            case_id=case_id,
            tenant_id="tenant-test",
            project_id=f"project-{case_id}",
            case_state="REVIEW_PENDING",
            review_state="PENDING",
            submission_mode="DIGITAL",
            portal_support_level="FULL",
            current_release_profile="default",
        )
        session.add(row)
        session.commit()


def _seed_review_decision(
    case_id: str,
    decision_id: str,
    outcome: str = "ACCEPT",
) -> None:
    """Insert a ReviewDecision row directly — satisfies the review gate for advancement.

    This lets the blocking-contradiction test confirm denial is from the contradiction
    guard (not a missing review).  outcome defaults to ACCEPT.
    """
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = ReviewDecision(
            decision_id=decision_id,
            schema_version="1.0",
            case_id=case_id,
            object_type="permit_case",
            object_id=case_id,
            idempotency_key=f"idem/{decision_id}",
            reviewer_id="reviewer-test",
            decision_outcome=outcome,
            reviewer_independence_status="PASS",
            dissent_flag=(outcome == "ACCEPT_WITH_DISSENT"),
            decision_at=dt.datetime.now(tz=dt.UTC),
        )
        session.add(row)
        session.commit()


def _make_transition_request(
    case_id: str,
    request_id: str | None = None,
    required_review_id: str | None = None,
) -> StateTransitionRequest:
    return StateTransitionRequest(
        request_id=request_id or str(uuid.uuid4()),
        case_id=case_id,
        from_state=CaseState.REVIEW_PENDING,
        to_state=CaseState.APPROVED_FOR_SUBMISSION,
        actor_type=ActorType.reviewer,
        actor_id="reviewer-test",
        correlation_id=str(uuid.uuid4()),
        required_review_id=required_review_id,
        required_evidence_ids=[],
        requested_at=dt.datetime.now(tz=dt.UTC),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_blocking_contradiction_denies_advancement() -> None:
    """Blocking contradiction → CONTRADICTION_ADVANCE_DENIED with stable identifiers."""
    asyncio.run(_run_blocking_contradiction_test())


def test_resolve_contradiction_allows_advancement() -> None:
    """Resolve blocking contradiction → next advancement succeeds (CASE_STATE_CHANGED)."""
    asyncio.run(_run_resolve_allows_advancement_test())


def test_nonblocking_contradiction_is_transparent() -> None:
    """Non-blocking contradiction → guard passes through to review check → APPROVAL_GATE_DENIED."""
    asyncio.run(_run_nonblocking_transparent_test())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_blocking_contradiction_test() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-CONTRA-BLOCK-001"
    contradiction_id = "CONTRA-BLOCK-001"
    decision_id = "DEC-CONTRA-BLOCK-001"

    # Seed case + review decision so the guard has a valid review to fall through to
    # if the contradiction guard didn't fire.
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.post(
            "/api/v1/contradictions/",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "contradiction_id": contradiction_id,
                "case_id": case_id,
                "scope": "zoning",
                "source_a": "applicant-submission",
                "source_b": "municipal-code-ref",
                "ranking_relation": "A_SUPERSEDES_B",
                "blocking_effect": True,
            },
        )

    assert response.status_code == 201, (
        f"Expected 201 from create contradiction, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body["resolution_status"] == "OPEN", f"Expected OPEN, got: {body}"

    # Call apply_state_transition directly — no Temporal worker required.
    req = _make_transition_request(
        case_id=case_id,
        request_id="REQ-CONTRA-BLOCK-001",
        required_review_id=decision_id,
    )
    result = apply_state_transition(req)

    assert isinstance(result, DeniedStateTransitionResult), (
        f"Expected DeniedStateTransitionResult, got: {type(result).__name__} — {result}"
    )
    assert result.event_type == "CONTRADICTION_ADVANCE_DENIED", (
        f"Expected CONTRADICTION_ADVANCE_DENIED, got: {result.event_type}"
    )
    assert result.guard_assertion_id == "INV-SPS-CONTRA-001", (
        f"Expected INV-SPS-CONTRA-001, got: {result.guard_assertion_id}"
    )
    assert result.normalized_business_invariants == ["INV-003"], (
        f"Expected ['INV-003'], got: {result.normalized_business_invariants}"
    )

    # Confirm ledger row was persisted with correct payload.
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        ledger_rows = list(
            session.execute(
                sa.text(
                    "SELECT event_type, payload FROM case_transition_ledger"
                    " WHERE case_id = :case_id ORDER BY occurred_at"
                ),
                {"case_id": case_id},
            ).fetchall()
        )
    assert len(ledger_rows) == 1, f"Expected 1 ledger row, got: {len(ledger_rows)}"
    event_type, payload = ledger_rows[0]
    assert event_type == "CONTRADICTION_ADVANCE_DENIED", (
        f"Ledger event_type mismatch: {event_type}"
    )
    assert payload.get("guard_assertion_id") == "INV-SPS-CONTRA-001", (
        f"Ledger payload guard_assertion_id mismatch: {payload}"
    )
    assert payload.get("normalized_business_invariants") == ["INV-003"], (
        f"Ledger payload normalized_business_invariants mismatch: {payload}"
    )


async def _run_resolve_allows_advancement_test() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-CONTRA-RESOLVE-001"
    contradiction_id = "CONTRA-RESOLVE-001"
    decision_id = "DEC-CONTRA-RESOLVE-001"

    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        # Create blocking contradiction.
        create_resp = await api_client.post(
            "/api/v1/contradictions/",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "contradiction_id": contradiction_id,
                "case_id": case_id,
                "scope": "floodplain",
                "source_a": "federal-regulation",
                "source_b": "local-ordinance",
                "ranking_relation": "A_SUPERSEDES_B",
                "blocking_effect": True,
            },
        )
        assert create_resp.status_code == 201, (
            f"Expected 201 from create contradiction, got {create_resp.status_code}: {create_resp.text}"
        )

        # Confirm first advancement is denied.
        first_req = _make_transition_request(
            case_id=case_id,
            request_id="REQ-CONTRA-RESOLVE-001-BEFORE",
            required_review_id=decision_id,
        )
        first_result = apply_state_transition(first_req)
        assert isinstance(first_result, DeniedStateTransitionResult), (
            f"Expected denial before resolve, got: {type(first_result).__name__}"
        )
        assert first_result.event_type == "CONTRADICTION_ADVANCE_DENIED"

        # Resolve the contradiction.
        resolve_resp = await api_client.post(
            f"/api/v1/contradictions/{contradiction_id}/resolve",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={"resolved_by": "reviewer-test"},
        )
        assert resolve_resp.status_code == 200, (
            f"Expected 200 from resolve, got {resolve_resp.status_code}: {resolve_resp.text}"
        )
        resolved_body = resolve_resp.json()
        assert resolved_body["resolution_status"] == "RESOLVED", (
            f"Expected RESOLVED, got: {resolved_body['resolution_status']}"
        )
        assert resolved_body["resolved_by"] == "reviewer-test", (
            f"Expected resolved_by=reviewer-test, got: {resolved_body['resolved_by']}"
        )

    # Now call apply_state_transition with a fresh request_id — contradiction is gone.
    second_req = _make_transition_request(
        case_id=case_id,
        request_id="REQ-CONTRA-RESOLVE-001-AFTER",
        required_review_id=decision_id,
    )
    second_result = apply_state_transition(second_req)

    assert isinstance(second_result, AppliedStateTransitionResult), (
        f"Expected AppliedStateTransitionResult after resolve, got: {type(second_result).__name__} — {second_result}"
    )
    assert second_result.event_type == "CASE_STATE_CHANGED", (
        f"Expected CASE_STATE_CHANGED, got: {second_result.event_type}"
    )

    # Confirm DB: contradiction is RESOLVED, case is APPROVED_FOR_SUBMISSION.
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        artifact = session.get(ContradictionArtifact, contradiction_id)
        assert artifact is not None
        assert artifact.resolution_status == "RESOLVED", (
            f"DB resolution_status mismatch: {artifact.resolution_status}"
        )
        assert artifact.resolved_at is not None, "resolved_at should be populated"
        assert artifact.resolved_by == "reviewer-test", (
            f"resolved_by mismatch: {artifact.resolved_by}"
        )

        case = session.get(PermitCase, case_id)
        assert case is not None
        assert case.case_state == "APPROVED_FOR_SUBMISSION", (
            f"Expected APPROVED_FOR_SUBMISSION, got: {case.case_state}"
        )


async def _run_nonblocking_transparent_test() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-CONTRA-NONBLOCK-001"
    contradiction_id = "CONTRA-NONBLOCK-001"

    _seed_permit_case(case_id)
    # No review decision seeded — the guard falls through to review check and should deny.

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.post(
            "/api/v1/contradictions/",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "contradiction_id": contradiction_id,
                "case_id": case_id,
                "scope": "setback",
                "source_a": "survey-report",
                "source_b": "applicant-plan",
                "ranking_relation": "A_SUPERSEDES_B",
                "blocking_effect": False,  # non-blocking — invisible to the guard
            },
        )

    assert response.status_code == 201, (
        f"Expected 201 from create contradiction, got {response.status_code}: {response.text}"
    )
    assert response.json()["blocking_effect"] is False

    # Call apply_state_transition without a valid review_id.
    req = _make_transition_request(
        case_id=case_id,
        request_id="REQ-CONTRA-NONBLOCK-001",
        required_review_id=None,  # no review — review gate will deny
    )
    result = apply_state_transition(req)

    assert isinstance(result, DeniedStateTransitionResult), (
        f"Expected DeniedStateTransitionResult, got: {type(result).__name__} — {result}"
    )
    # Must be the review-gate denial, NOT the contradiction guard denial.
    assert result.event_type == "APPROVAL_GATE_DENIED", (
        f"Expected APPROVAL_GATE_DENIED (non-blocking contradiction transparent),"
        f" got: {result.event_type}"
    )
    # Contradiction guard identifiers must NOT appear — this was the review gate.
    assert result.guard_assertion_id != "INV-SPS-CONTRA-001", (
        f"Non-blocking contradiction must NOT produce INV-SPS-CONTRA-001 denial,"
        f" got: {result.guard_assertion_id}"
    )
