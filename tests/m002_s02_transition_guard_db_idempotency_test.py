from __future__ import annotations

import datetime as dt
import os
import time

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from sps.db.models import CaseTransitionLedger, PermitCase, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import apply_state_transition
from sps.workflows.permit_case.contracts import ActorType, CaseState, StateTransitionRequest


pytestmark = pytest.mark.integration

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "DB-backed integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


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

    raise RuntimeError(f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})")


@pytest.fixture(scope="session", autouse=True)
def _migrate_db() -> None:
    _wait_for_postgres_ready()
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture()
def db_session() -> Session:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE case_transition_ledger, review_decisions, permit_cases CASCADE"
            )
        )

    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_case(db_session: Session, *, case_id: str, state: CaseState) -> None:
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=state.value,
            review_state="PENDING",
            submission_mode="PORTAL",
            portal_support_level="SELF_SERVICE",
            current_package_id=None,
            current_release_profile="default",
            closure_reason=None,
            legal_hold=False,
        )
    )
    db_session.commit()


def _seed_review_decision(db_session: Session, *, decision_id: str, case_id: str, outcome: str) -> None:
    db_session.add(
        ReviewDecision(
            decision_id=decision_id,
            schema_version="1.0.0",
            case_id=case_id,
            object_type="PermitCase",
            object_id=case_id,
            decision_outcome=outcome,
            reviewer_id="USR-REVIEW-01",
            reviewer_independence_status="PASS",
            evidence_ids=[],
            contradiction_resolution=None,
            dissent_flag=False,
            notes=None,
            decision_at=_utcnow(),
            idempotency_key=f"idem-{decision_id}",
        )
    )
    db_session.commit()


def test_idempotent_applied_transition_writes_ledger_once(db_session: Session) -> None:
    case_id = "CASE-IDEMPOTENT-APPLIED"
    decision_id = "REV-APPLIED-001"

    _seed_case(db_session, case_id=case_id, state=CaseState.REVIEW_PENDING)
    _seed_review_decision(db_session, decision_id=decision_id, case_id=case_id, outcome="ACCEPT")

    req = StateTransitionRequest(
        request_id="REQ-APPLIED-001",
        case_id=case_id,
        from_state=CaseState.REVIEW_PENDING,
        to_state=CaseState.APPROVED_FOR_SUBMISSION,
        actor_type=ActorType.system_guard,
        actor_id="system-guard",
        correlation_id="CORR-APPLIED-001",
        causation_id=None,
        required_review_id=decision_id,
        required_evidence_ids=[],
        override_id=None,
        requested_at=_utcnow(),
        notes=None,
    )

    r1 = apply_state_transition(req)
    assert r1.result == "applied"
    assert r1.event_type == "CASE_STATE_CHANGED"

    db_session.expire_all()
    reloaded = db_session.get(PermitCase, case_id)
    assert reloaded is not None
    assert reloaded.case_state == CaseState.APPROVED_FOR_SUBMISSION.value

    ledgers = db_session.query(CaseTransitionLedger).filter_by(transition_id=req.request_id).all()
    assert len(ledgers) == 1
    assert ledgers[0].event_type == "CASE_STATE_CHANGED"
    assert ledgers[0].payload is not None
    assert ledgers[0].payload.get("result") == "applied"

    # Re-applying the same request_id must return the persisted prior outcome.
    r2 = apply_state_transition(req)
    assert r2.result == "applied"
    assert r2.event_type == "CASE_STATE_CHANGED"

    ledgers_after = (
        db_session.query(CaseTransitionLedger).filter_by(transition_id=req.request_id).all()
    )
    assert len(ledgers_after) == 1


def test_idempotent_denied_transition_persists_stable_guard_payload(db_session: Session) -> None:
    case_id = "CASE-IDEMPOTENT-DENIED"

    _seed_case(db_session, case_id=case_id, state=CaseState.REVIEW_PENDING)

    req = StateTransitionRequest(
        request_id="REQ-DENIED-001",
        case_id=case_id,
        from_state=CaseState.REVIEW_PENDING,
        to_state=CaseState.APPROVED_FOR_SUBMISSION,
        actor_type=ActorType.system_guard,
        actor_id="system-guard",
        correlation_id="CORR-DENIED-001",
        causation_id=None,
        required_review_id=None,
        required_evidence_ids=[],
        override_id=None,
        requested_at=_utcnow(),
        notes=None,
    )

    r1 = apply_state_transition(req)
    assert r1.result == "denied"
    assert r1.event_type == "APPROVAL_GATE_DENIED"
    assert r1.guard_assertion_id == "INV-SPS-STATE-002"
    assert r1.normalized_business_invariants is not None
    assert "INV-001" in r1.normalized_business_invariants

    db_session.expire_all()
    reloaded = db_session.get(PermitCase, case_id)
    assert reloaded is not None
    assert reloaded.case_state == CaseState.REVIEW_PENDING.value

    ledgers = db_session.query(CaseTransitionLedger).filter_by(transition_id=req.request_id).all()
    assert len(ledgers) == 1
    ledger = ledgers[0]
    assert ledger.event_type == "APPROVAL_GATE_DENIED"
    assert ledger.payload is not None
    assert ledger.payload.get("guard_assertion_id") == "INV-SPS-STATE-002"
    invs = ledger.payload.get("normalized_business_invariants")
    assert isinstance(invs, list)
    assert "INV-001" in invs

    # Re-applying the same request_id must return the persisted prior outcome.
    r2 = apply_state_transition(req)
    assert r2.result == "denied"
    assert r2.event_type == "APPROVAL_GATE_DENIED"

    ledgers_after = (
        db_session.query(CaseTransitionLedger).filter_by(transition_id=req.request_id).all()
    )
    assert len(ledgers_after) == 1
