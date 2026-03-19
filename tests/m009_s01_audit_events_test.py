"""M009 / S01 integration test: audit event persistence.

Guard: set SPS_RUN_TEMPORAL_INTEGRATION=1 to run this file.

Checks:
  - Review decision creation writes an audit_events row with correlation metadata.
  - State transition denial writes an audit_events row with correlation metadata.
"""
from __future__ import annotations

import datetime as dt
import os
import time

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import ulid

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import AuditEvent, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import apply_state_transition
from sps.workflows.permit_case.contracts import ActorType, CaseState, StateTransitionRequest


pytestmark = pytest.mark.integration

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal/Postgres integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
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
                "TRUNCATE TABLE audit_events, case_transition_ledger, review_decisions, permit_cases CASCADE"
            )
        )


def _seed_case(case_id: str, *, case_state: str = "REVIEW_PENDING") -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.add(
            PermitCase(
                case_id=case_id,
                tenant_id="tenant-test",
                project_id=f"PROJ-{case_id}",
                case_state=case_state,
                review_state="PENDING",
                submission_mode="PORTAL",
                portal_support_level="FULL",
                current_package_id=None,
                current_release_profile="default",
                legal_hold=False,
                closure_reason=None,
            )
        )
        session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_review_decision_emits_audit_event() -> None:
    settings = get_settings()

    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = f"CASE-{ulid.new()}"
    _seed_case(case_id)

    decision_id = f"DEC-{ulid.new()}"
    idempotency_key = f"idem/{decision_id}"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/reviews/decisions",
            headers={"X-Reviewer-Api-Key": settings.reviewer_api_key},
            json={
                "decision_id": decision_id,
                "idempotency_key": idempotency_key,
                "case_id": case_id,
                "reviewer_id": "reviewer-audit-test",
                "subject_author_id": "author-audit-test",
                "outcome": "ACCEPT",
            },
        )

    assert response.status_code == 201, (
        f"Expected 201 from reviewer API, got {response.status_code}: {response.text}"
    )

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        event = (
            session.query(AuditEvent)
            .filter(
                AuditEvent.action == "review_decision.created",
                AuditEvent.request_id == decision_id,
            )
            .first()
        )
        assert event is not None, "audit_events row missing for review_decision.created"
        assert event.correlation_id == case_id
        assert event.actor_type == "reviewer"
        assert event.actor_id == "reviewer-audit-test"
        assert event.payload is not None
        assert event.payload.get("decision_outcome") == "ACCEPT"
        assert event.payload.get("idempotency_key") == idempotency_key


def test_state_transition_denied_emits_audit_event() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = f"CASE-{ulid.new()}"
    _seed_case(case_id)

    request_id = f"transition/{case_id}"
    correlation_id = f"corr/{case_id}"

    result = apply_state_transition(
        StateTransitionRequest(
            request_id=request_id,
            case_id=case_id,
            from_state=CaseState.REVIEW_PENDING,
            to_state=CaseState.APPROVED_FOR_SUBMISSION,
            actor_type=ActorType.system_guard,
            actor_id="system-guard",
            correlation_id=correlation_id,
            causation_id=None,
            required_review_id=None,
            required_evidence_ids=[],
            override_id=None,
            requested_at=dt.datetime.now(dt.UTC),
            notes=None,
        )
    )

    assert result.result == "denied"
    assert result.event_type == "APPROVAL_GATE_DENIED"

    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        event = (
            session.query(AuditEvent)
            .filter(
                AuditEvent.action == "state_transition.denied",
                AuditEvent.request_id == request_id,
            )
            .first()
        )
        assert event is not None, "audit_events row missing for state_transition.denied"
        assert event.correlation_id == correlation_id
        assert event.actor_type == ActorType.system_guard.value
        assert event.actor_id == "system-guard"
        assert event.payload is not None
        assert event.payload.get("event_type") == "APPROVAL_GATE_DENIED"
