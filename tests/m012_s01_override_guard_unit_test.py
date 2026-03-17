"""M012 / S01 unit tests: override guard in apply_state_transition.

Proves override guard enforcement and pass-through behavior against real Postgres
(no Temporal worker required).

Scenarios:
  1. override_id=None → review gate applies, transition allowed with valid review.
  2. override_id missing → OVERRIDE_DENIED + guard assertion metadata.
  3. override expired → OVERRIDE_DENIED.
  4. override out of scope → OVERRIDE_DENIED.
  5. valid override → transition allowed.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.db.models import OverrideArtifact, PermitCase, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker
from sps.guards.guard_assertions import get_normalized_business_invariants
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

_OVERRIDE_GUARD_ASSERTION = "INV-SPS-EMERG-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_for_postgres_ready(timeout_s: float = 30.0) -> None:
    deadline = dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=timeout_s)
    engine = get_engine()
    last_exc: Exception | None = None
    while dt.datetime.now(tz=dt.UTC) < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            import time

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
                "TRUNCATE TABLE case_transition_ledger, review_decisions, override_artifacts, permit_cases CASCADE"
            )
        )


def _seed_permit_case(case_id: str) -> None:
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


def _seed_review_decision(case_id: str, decision_id: str) -> None:
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
            decision_outcome="ACCEPT",
            reviewer_independence_status="PASS",
            dissent_flag=False,
            decision_at=dt.datetime.now(tz=dt.UTC),
        )
        session.add(row)
        session.commit()


def _seed_override(
    *,
    override_id: str,
    case_id: str,
    expires_at: dt.datetime,
    affected_surfaces: list[str],
) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = OverrideArtifact(
            override_id=override_id,
            case_id=case_id,
            scope="reviewer_independence",
            justification="Emergency bypass",
            start_at=expires_at - dt.timedelta(hours=1),
            expires_at=expires_at,
            affected_surfaces=affected_surfaces,
            approver_id="escalation-owner",
            cleanup_required=True,
        )
        session.add(row)
        session.commit()


def _make_request(
    *,
    case_id: str,
    request_id: str,
    required_review_id: str,
    override_id: str | None,
    requested_at: dt.datetime,
) -> StateTransitionRequest:
    return StateTransitionRequest(
        request_id=request_id,
        case_id=case_id,
        from_state=CaseState.REVIEW_PENDING,
        to_state=CaseState.APPROVED_FOR_SUBMISSION,
        actor_type=ActorType.reviewer,
        actor_id="reviewer-test",
        correlation_id=str(uuid.uuid4()),
        required_review_id=required_review_id,
        required_evidence_ids=[],
        override_id=override_id,
        requested_at=requested_at,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_override_id_allows() -> None:
    asyncio.run(_run_no_override_id_allows())


def test_nonexistent_override_denies() -> None:
    asyncio.run(_run_nonexistent_override_denies())


def test_expired_override_denies() -> None:
    asyncio.run(_run_expired_override_denies())


def test_out_of_scope_override_denies() -> None:
    asyncio.run(_run_out_of_scope_override_denies())


def test_valid_override_allows() -> None:
    asyncio.run(_run_valid_override_allows())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_no_override_id_allows() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-001"
    decision_id = "DEC-OVR-GUARD-001"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    requested_at = dt.datetime.now(tz=dt.UTC)
    req = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-001",
        required_review_id=decision_id,
        override_id=None,
        requested_at=requested_at,
    )

    result = apply_state_transition(req)
    assert isinstance(result, AppliedStateTransitionResult)
    assert result.event_type == "CASE_STATE_CHANGED"


async def _run_nonexistent_override_denies() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-002"
    decision_id = "DEC-OVR-GUARD-002"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    requested_at = dt.datetime.now(tz=dt.UTC)
    req = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-002",
        required_review_id=decision_id,
        override_id="OVR-MISSING-001",
        requested_at=requested_at,
    )

    result = apply_state_transition(req)
    assert isinstance(result, DeniedStateTransitionResult)
    assert result.event_type == "OVERRIDE_DENIED"
    assert result.guard_assertion_id == _OVERRIDE_GUARD_ASSERTION
    assert result.normalized_business_invariants == get_normalized_business_invariants(
        _OVERRIDE_GUARD_ASSERTION
    )

    _assert_ledger_denial(case_id)


async def _run_expired_override_denies() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-003"
    decision_id = "DEC-OVR-GUARD-003"
    override_id = "OVR-EXPIRED-001"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    expired_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(hours=1)
    _seed_override(
        override_id=override_id,
        case_id=case_id,
        expires_at=expired_at,
        affected_surfaces=["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"],
    )

    requested_at = dt.datetime.now(tz=dt.UTC)
    req = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-003",
        required_review_id=decision_id,
        override_id=override_id,
        requested_at=requested_at,
    )

    result = apply_state_transition(req)
    assert isinstance(result, DeniedStateTransitionResult)
    assert result.event_type == "OVERRIDE_DENIED"
    assert result.guard_assertion_id == _OVERRIDE_GUARD_ASSERTION

    _assert_ledger_denial(case_id)


async def _run_out_of_scope_override_denies() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-004"
    decision_id = "DEC-OVR-GUARD-004"
    override_id = "OVR-SCOPE-001"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(hours=2)
    _seed_override(
        override_id=override_id,
        case_id=case_id,
        expires_at=expires_at,
        affected_surfaces=["REVIEW_PENDING->SUBMISSION_PENDING"],
    )

    requested_at = dt.datetime.now(tz=dt.UTC)
    req = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-004",
        required_review_id=decision_id,
        override_id=override_id,
        requested_at=requested_at,
    )

    result = apply_state_transition(req)
    assert isinstance(result, DeniedStateTransitionResult)
    assert result.event_type == "OVERRIDE_DENIED"
    assert result.guard_assertion_id == _OVERRIDE_GUARD_ASSERTION

    _assert_ledger_denial(case_id)


async def _run_valid_override_allows() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-005"
    decision_id = "DEC-OVR-GUARD-005"
    override_id = "OVR-VALID-001"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(hours=2)
    _seed_override(
        override_id=override_id,
        case_id=case_id,
        expires_at=expires_at,
        affected_surfaces=["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"],
    )

    requested_at = dt.datetime.now(tz=dt.UTC)
    req = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-005",
        required_review_id=decision_id,
        override_id=override_id,
        requested_at=requested_at,
    )

    result = apply_state_transition(req)
    assert isinstance(result, AppliedStateTransitionResult)
    assert result.event_type == "CASE_STATE_CHANGED"


def _assert_ledger_denial(case_id: str) -> None:
    invariants = get_normalized_business_invariants(_OVERRIDE_GUARD_ASSERTION)
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        rows = list(
            session.execute(
                sa.text(
                    "SELECT event_type, payload FROM case_transition_ledger"
                    " WHERE case_id = :case_id ORDER BY occurred_at"
                ),
                {"case_id": case_id},
            ).fetchall()
        )
    assert len(rows) == 1, f"Expected 1 ledger row, got {len(rows)}"
    event_type, payload = rows[0]
    assert event_type == "OVERRIDE_DENIED"
    assert payload.get("guard_assertion_id") == _OVERRIDE_GUARD_ASSERTION
    assert payload.get("normalized_business_invariants") == invariants
