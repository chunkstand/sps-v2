from __future__ import annotations

import asyncio
import datetime as dt
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import timedelta

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from temporalio import workflow
from temporalio.worker import Worker

from sps.config import get_settings
from sps.db.models import (
    CaseTransitionLedger,
    ContradictionArtifact,
    OverrideArtifact,
    PermitCase,
    ReviewDecision,
)
from sps.db.session import get_engine, get_sessionmaker

with workflow.unsafe.imports_passed_through():
    from sps.guards.guard_assertions import get_normalized_business_invariants
    from sps.workflows.permit_case.activities import apply_state_transition
from sps.workflows.permit_case.contracts import (
    ActorType,
    AppliedStateTransitionResult,
    CaseState,
    DeniedStateTransitionResult,
    StateTransitionRequest,
    parse_state_transition_result,
)
from sps.workflows.temporal import connect_client

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )

_OVERRIDE_GUARD_ASSERTION = "INV-SPS-EMERG-001"


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


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _reset_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE case_transition_ledger, review_decisions, "
                "contradiction_artifacts, override_artifacts, permit_cases CASCADE"
            )
        )


async def _connect_temporal_with_retry(timeout_s: float = 30.0):
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            return await connect_client()
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            await asyncio.sleep(0.5)

    raise RuntimeError(
        f"Temporal not ready after {timeout_s}s (last_exc={type(last_exc).__name__})"
    )


@workflow.defn
class OverrideGuardWorkflow:
    @workflow.run
    async def run(self, request: StateTransitionRequest) -> dict:
        raw_result = await workflow.execute_activity(
            apply_state_transition,
            request,
            start_to_close_timeout=timedelta(seconds=30),
        )
        if hasattr(raw_result, "model_dump"):
            return raw_result.model_dump()
        if isinstance(raw_result, dict):
            return raw_result
        return raw_result.__dict__


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


def _seed_blocking_contradiction(case_id: str, contradiction_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        row = ContradictionArtifact(
            contradiction_id=contradiction_id,
            case_id=case_id,
            scope="zoning",
            source_a="applicant-submission",
            source_b="municipal-code-ref",
            ranking_relation="A_SUPERSEDES_B",
            blocking_effect=True,
            resolution_status="OPEN",
            resolved_at=None,
            resolved_by=None,
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


def _fetch_ledger_rows(case_id: str) -> list[CaseTransitionLedger]:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        return (
            session.query(CaseTransitionLedger)
            .filter(CaseTransitionLedger.case_id == case_id)
            .order_by(CaseTransitionLedger.occurred_at.asc())
            .all()
        )


async def _run_transition(request: StateTransitionRequest):
    client = await _connect_temporal_with_retry()
    settings = get_settings()

    executor = ThreadPoolExecutor(max_workers=4)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[OverrideGuardWorkflow],
        activities=[apply_state_transition],
        activity_executor=executor,
    )

    worker_task = asyncio.create_task(worker.run())
    try:
        workflow_id = f"override-guard/{request.case_id}/{uuid.uuid4()}"
        handle = await client.start_workflow(
            OverrideGuardWorkflow.run,
            request,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        raw_result = await asyncio.wait_for(handle.result(), timeout=30.0)
        return parse_state_transition_result(raw_result)
    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)


def test_transition_allows_without_override() -> None:
    asyncio.run(_run_transition_allows_without_override())


def test_nonexistent_override_denies() -> None:
    asyncio.run(_run_nonexistent_override_denies())


def test_expired_override_denies() -> None:
    asyncio.run(_run_expired_override_denies())


def test_valid_override_allows() -> None:
    asyncio.run(_run_valid_override_allows())


async def _run_transition_allows_without_override() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-INT-001"
    decision_id = "DEC-OVR-GUARD-INT-001"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    requested_at = dt.datetime.now(tz=dt.UTC)
    request = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-INT-001",
        required_review_id=decision_id,
        override_id=None,
        requested_at=requested_at,
    )

    result = await _run_transition(request)
    assert isinstance(result, AppliedStateTransitionResult)
    assert result.event_type == "CASE_STATE_CHANGED"

    rows = _fetch_ledger_rows(case_id)
    assert len(rows) == 1
    assert rows[0].event_type == "CASE_STATE_CHANGED"


async def _run_nonexistent_override_denies() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-INT-002"
    decision_id = "DEC-OVR-GUARD-INT-002"
    contradiction_id = "CONTRA-OVR-GUARD-INT-002"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)
    _seed_blocking_contradiction(case_id, contradiction_id)

    requested_at = dt.datetime.now(tz=dt.UTC)
    request = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-INT-002",
        required_review_id=decision_id,
        override_id="OVR-NONEXISTENT",
        requested_at=requested_at,
    )

    result = await _run_transition(request)
    assert isinstance(result, DeniedStateTransitionResult)
    assert result.event_type == "OVERRIDE_DENIED"
    assert result.guard_assertion_id == _OVERRIDE_GUARD_ASSERTION
    assert result.normalized_business_invariants == get_normalized_business_invariants(
        _OVERRIDE_GUARD_ASSERTION
    )

    rows = _fetch_ledger_rows(case_id)
    assert len(rows) == 1
    payload = rows[0].payload or {}
    assert rows[0].event_type == "OVERRIDE_DENIED"
    assert payload.get("guard_assertion_id") == _OVERRIDE_GUARD_ASSERTION
    assert payload.get("normalized_business_invariants") == get_normalized_business_invariants(
        _OVERRIDE_GUARD_ASSERTION
    )


async def _run_expired_override_denies() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-INT-003"
    decision_id = "DEC-OVR-GUARD-INT-003"
    override_id = "OVR-EXPIRED-INT-003"
    _seed_permit_case(case_id)
    _seed_review_decision(case_id, decision_id)

    expires_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(hours=1)
    _seed_override(
        override_id=override_id,
        case_id=case_id,
        expires_at=expires_at,
        affected_surfaces=["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"],
    )

    requested_at = dt.datetime.now(tz=dt.UTC)
    request = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-INT-003",
        required_review_id=decision_id,
        override_id=override_id,
        requested_at=requested_at,
    )

    result = await _run_transition(request)
    assert isinstance(result, DeniedStateTransitionResult)
    assert result.event_type == "OVERRIDE_DENIED"
    assert result.denial_reason == "expired"
    assert result.guard_assertion_id == _OVERRIDE_GUARD_ASSERTION

    rows = _fetch_ledger_rows(case_id)
    assert len(rows) == 1
    payload = rows[0].payload or {}
    assert rows[0].event_type == "OVERRIDE_DENIED"
    assert payload.get("guard_assertion_id") == _OVERRIDE_GUARD_ASSERTION
    assert payload.get("normalized_business_invariants") == get_normalized_business_invariants(
        _OVERRIDE_GUARD_ASSERTION
    )


async def _run_valid_override_allows() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-OVR-GUARD-INT-004"
    decision_id = "DEC-OVR-GUARD-INT-004"
    override_id = "OVR-VALID-INT-004"
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
    request = _make_request(
        case_id=case_id,
        request_id="REQ-OVR-GUARD-INT-004",
        required_review_id=decision_id,
        override_id=override_id,
        requested_at=requested_at,
    )

    result = await _run_transition(request)
    assert isinstance(result, AppliedStateTransitionResult)
    assert result.event_type == "CASE_STATE_CHANGED"

    rows = _fetch_ledger_rows(case_id)
    assert len(rows) == 1
    assert rows[0].event_type == "CASE_STATE_CHANGED"
