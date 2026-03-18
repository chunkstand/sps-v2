"""M003 / S04 integration tests: Dissent artifact creation and read endpoint.

Proves R009 end-to-end against real Postgres (no Temporal worker needed).

Two scenarios:

  1. ACCEPT_WITH_DISSENT creates a queryable dissent artifact:
       - seed permit_case
       - POST /api/v1/reviews/decisions with outcome=ACCEPT_WITH_DISSENT
         + dissent_scope + dissent_rationale → 201
       - dissent_artifact_id present in response
       - GET /api/v1/dissents/{dissent_id} → 200; linked_review_id, case_id,
         scope, resolution_state all match expected values
       - DB confirms row exists in dissent_artifacts

  2. ACCEPT does not create a dissent artifact:
       - seed permit_case
       - POST /api/v1/reviews/decisions with outcome=ACCEPT → 201
       - dissent_artifact_id absent from response
       - DB confirms no row in dissent_artifacts linked to the decision

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.
Pattern: mirrors m003_s03 (real Postgres, no Temporal worker needed).

## Observability Impact

Signals documented by these tests:
  - reviewer_api.dissent_artifact_created  dissent_id=... linked_review_id=... case_id=... scope_len=...
    Fires once per ACCEPT_WITH_DISSENT decision, before commit. Confirmed via log inspection.
  - reviewer_api.dissent_validation_rejected — surfaced as HTTP 422 with field paths
    dissent_scope / dissent_rationale when those fields are missing.

Diagnostic inspection:
  - SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts;
  - GET /api/v1/dissents/{dissent_id} — 200 + full artifact, or 404 + {"error": "not_found"}

Failure state visibility:
  - Missing dissent fields on ACCEPT_WITH_DISSENT → HTTP 422 + Pydantic detail listing paths
  - Transaction rollback → both ReviewDecision and DissentArtifact absent from DB
  - FK violation → DB IntegrityError → HTTP 500; check postgres logs for constraint name
"""

from __future__ import annotations

import asyncio
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
from sps.db.models import DissentArtifact, PermitCase
from sps.db.session import get_engine, get_sessionmaker

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
    """Truncate all test-relevant tables.

    Order matters: dissent_artifacts references review_decisions (RESTRICT), so we
    truncate dissent_artifacts before review_decisions. permit_cases CASCADE will also
    remove any dissent_artifacts with a matching case_id FK, but we truncate explicitly
    to avoid relying on ordering assumptions in CASCADE chains.
    """
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE dissent_artifacts, case_transition_ledger,"
                " review_decisions, contradiction_artifacts, permit_cases CASCADE"
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


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _db_lifecycle() -> None:  # type: ignore[return]
    _wait_for_postgres_ready()
    _migrate_db()
    yield
    _reset_db()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_accept_with_dissent_creates_artifact() -> None:
    """ACCEPT_WITH_DISSENT → dissent artifact created, queryable via GET endpoint."""
    asyncio.run(_run_accept_with_dissent_creates_artifact())


def test_accept_does_not_create_artifact() -> None:
    """ACCEPT → no dissent artifact created; DB confirms absence."""
    asyncio.run(_run_accept_does_not_create_artifact())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_accept_with_dissent_creates_artifact() -> None:
    settings = get_settings()

    case_id = "CASE-DISSENT-ACCEPT-WITH-001"
    decision_id = f"DEC-DISSENT-AWD-{uuid.uuid4().hex[:8]}"
    idempotency_key = f"idem/{decision_id}"

    _seed_permit_case(case_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # POST ACCEPT_WITH_DISSENT decision.
        response = await client.post(
            "/api/v1/reviews/decisions",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "decision_id": decision_id,
                "idempotency_key": idempotency_key,
                "case_id": case_id,
                "reviewer_id": "reviewer-test-dissent",
                "subject_author_id": "author-of-the-case",
                "outcome": "ACCEPT_WITH_DISSENT",
                "dissent_scope": "structural",
                "dissent_rationale": "reviewer notes structural concern",
            },
        )

    assert response.status_code == 201, (
        f"Expected 201 from POST /api/v1/reviews/decisions, got {response.status_code}: {response.text}"
    )
    body = response.json()

    dissent_artifact_id = body.get("dissent_artifact_id")
    assert dissent_artifact_id is not None, (
        f"Expected dissent_artifact_id in response, got: {body}"
    )

    # GET /api/v1/dissents/{dissent_id} — read endpoint.
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        get_response = await client.get(
            f"/api/v1/dissents/{dissent_artifact_id}",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
        )

    assert get_response.status_code == 200, (
        f"Expected 200 from GET /api/v1/dissents/{dissent_artifact_id},"
        f" got {get_response.status_code}: {get_response.text}"
    )
    artifact = get_response.json()

    assert artifact["linked_review_id"] == decision_id, (
        f"linked_review_id mismatch: expected {decision_id}, got {artifact.get('linked_review_id')}"
    )
    assert artifact["case_id"] == case_id, (
        f"case_id mismatch: expected {case_id}, got {artifact.get('case_id')}"
    )
    assert artifact["scope"] == "structural", (
        f"scope mismatch: expected 'structural', got {artifact.get('scope')}"
    )
    assert artifact["resolution_state"] == "OPEN", (
        f"resolution_state mismatch: expected 'OPEN', got {artifact.get('resolution_state')}"
    )

    # DB confirmation — not just HTTP assertions.
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        db_row = session.get(DissentArtifact, dissent_artifact_id)
        assert db_row is not None, (
            f"DissentArtifact row not found in DB: dissent_id={dissent_artifact_id}"
        )
        assert db_row.linked_review_id == decision_id, (
            f"DB linked_review_id mismatch: {db_row.linked_review_id}"
        )
        assert db_row.case_id == case_id, (
            f"DB case_id mismatch: {db_row.case_id}"
        )
        assert db_row.scope == "structural", (
            f"DB scope mismatch: {db_row.scope}"
        )
        assert db_row.resolution_state == "OPEN", (
            f"DB resolution_state mismatch: {db_row.resolution_state}"
        )


async def _run_accept_does_not_create_artifact() -> None:
    settings = get_settings()

    case_id = "CASE-DISSENT-ACCEPT-PLAIN-001"
    decision_id = f"DEC-DISSENT-ACC-{uuid.uuid4().hex[:8]}"
    idempotency_key = f"idem/{decision_id}"

    _seed_permit_case(case_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/reviews/decisions",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "decision_id": decision_id,
                "idempotency_key": idempotency_key,
                "case_id": case_id,
                "reviewer_id": "reviewer-test-plain",
                "subject_author_id": "author-of-the-case",
                "outcome": "ACCEPT",
            },
        )

    assert response.status_code == 201, (
        f"Expected 201 from POST /api/v1/reviews/decisions (ACCEPT),"
        f" got {response.status_code}: {response.text}"
    )
    body = response.json()

    assert body.get("dissent_artifact_id") is None, (
        f"Expected dissent_artifact_id to be None for ACCEPT outcome, got: {body.get('dissent_artifact_id')}"
    )

    # DB confirmation — no row with linked_review_id == decision_id.
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        result = session.execute(
            sa.text(
                "SELECT COUNT(*) FROM dissent_artifacts WHERE linked_review_id = :decision_id"
            ),
            {"decision_id": decision_id},
        ).scalar()
        assert result == 0, (
            f"Expected 0 dissent_artifacts rows for decision_id={decision_id}, got: {result}"
        )
