"""M012 / S01 integration tests: EMERGENCY_HOLD lifecycle transitions.

Covers:
- EmergencyHoldEntry signal with valid emergency artifact (HTTP-created) enters EMERGENCY_HOLD.
- Forbidden EMERGENCY_HOLD -> SUBMITTED transition is denied (spec section 9.3).
- EmergencyHoldExit signal with reviewer confirmation (HTTP-created) exits to REVIEW_PENDING.

## Observability Impact

Signals and artifacts validated here:
- workflow.emergency_hold_entered / workflow.emergency_hold_exited logs (implicit via signals).
- case_transition_ledger CASE_STATE_CHANGED rows for EMERGENCY_HOLD entry/exit.
- case_transition_ledger STATE_TRANSITION_DENIED row for forbidden EMERGENCY_HOLD -> SUBMITTED.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress

import httpx
import pytest
import sqlalchemy as sa
import ulid
from alembic import command
from alembic.config import Config
from temporalio.worker import Worker

from sps.api.main import app
from sps.config import get_settings
from sps.db.models import CaseTransitionLedger, PermitCase
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    validate_emergency_artifact,
    validate_reviewer_confirmation,
)
from sps.workflows.permit_case.contracts import (
    ActorType,
    CaseState,
    DeniedStateTransitionResult,
    EmergencyHoldExitRequest,
    EmergencyHoldRequest,
    PermitCaseWorkflowInput,
    StateTransitionRequest,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client
from tests.helpers.auth_tokens import build_jwt

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
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

    raise RuntimeError(f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})")


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _reset_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE case_transition_ledger, review_decisions, emergency_records, permit_cases CASCADE"
            )
        )


def _seed_case(case_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        case = PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=CaseState.REVIEW_PENDING.value,
            review_state="PENDING",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
        session.add(case)
        session.commit()


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


def _transition_request_id(*, workflow_id: str, run_id: str, transition: str, attempt: int) -> str:
    return f"{workflow_id}/{run_id}/{transition}/attempt-{attempt}"


def _new_id(prefix: str) -> str:
    return f"{prefix}-{ulid.new()}"


async def _wait_for_ledger_row(transition_id: str, timeout_s: float = 10.0) -> CaseTransitionLedger:
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            row = session.get(CaseTransitionLedger, transition_id)
            if row is not None:
                return row
        await asyncio.sleep(0.25)

    raise AssertionError(
        f"case_transition_ledger row not found for transition_id={transition_id} within {timeout_s}s"
    )


async def _wait_for_initial_review_denial(workflow_id: str, run_id: str) -> None:
    denial_request_id = _transition_request_id(
        workflow_id=workflow_id,
        run_id=run_id,
        transition="review_pending_to_approved_for_submission",
        attempt=1,
    )
    row = await _wait_for_ledger_row(denial_request_id)
    assert row.event_type == "APPROVAL_GATE_DENIED"


async def _declare_emergency(case_id: str) -> str:
    token = build_jwt(subject="escalation-user-1", roles=["escalation-owner"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/emergencies/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "incident_id": f"INC-{case_id}",
                "case_id": case_id,
                "scope": "full_case",
                "allowed_bypasses": ["WORKFLOW_GUARD_SKIP"],
                "forbidden_bypasses": [],
            },
        )

    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    body = response.json()
    return body["emergency_id"]


async def _create_review_decision(case_id: str, decision_id: str) -> None:
    token = build_jwt(subject="reviewer-emergency-hold", roles=["reviewer"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/reviews/decisions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "decision_id": decision_id,
                "idempotency_key": f"idem/{decision_id}",
                "case_id": case_id,
                "reviewer_id": "reviewer-emergency-hold",
                "subject_author_id": "author-emergency-hold",
                "outcome": "ACCEPT",
            },
        )

    assert response.status_code == 201, (
        f"Expected 201 from reviewer API, got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_AUTH_JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("SPS_AUTH_JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SPS_AUTH_JWT_ALGORITHM", "HS256")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_emergency_hold_entry_with_valid_emergency(auth_env: None) -> None:
    asyncio.run(_run_emergency_hold_entry())


def test_emergency_hold_forbidden_transition(auth_env: None) -> None:
    asyncio.run(_run_emergency_hold_forbidden_transition())


def test_emergency_hold_exit_with_reviewer_confirmation(auth_env: None) -> None:
    asyncio.run(_run_emergency_hold_exit())


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_emergency_hold_entry() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = _new_id("CASE-EMERG-HOLD-ENTRY")
    _seed_case(case_id)

    client = await _connect_temporal_with_retry()
    settings = get_settings()

    executor = ThreadPoolExecutor(max_workers=10)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PermitCaseWorkflow],
        activities=[
            ensure_permit_case_exists,
            fetch_permit_case_state,
            apply_state_transition,
            validate_emergency_artifact,
            validate_reviewer_confirmation,
        ],
        activity_executor=executor,
    )

    worker_task = asyncio.create_task(worker.run())
    handle = None
    try:
        workflow_id = permit_case_workflow_id(case_id)
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            PermitCaseWorkflowInput(case_id=case_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        run_id = handle.first_execution_run_id or handle.run_id
        assert run_id is not None

        await _wait_for_initial_review_denial(workflow_id, run_id)

        emergency_id = await _declare_emergency(case_id)
        await handle.signal("EmergencyHoldEntry", EmergencyHoldRequest(emergency_id=emergency_id))

        entry_request_id = _transition_request_id(
            workflow_id=workflow_id,
            run_id=run_id,
            transition="emergency_hold_entry",
            attempt=1,
        )
        row = await _wait_for_ledger_row(entry_request_id)
        assert row.event_type == "CASE_STATE_CHANGED"
        assert row.from_state == CaseState.REVIEW_PENDING.value
        assert row.to_state == CaseState.EMERGENCY_HOLD.value
        assert row.correlation_id == f"{workflow_id}:{run_id}"

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            case = session.get(PermitCase, case_id)
            assert case is not None
            assert case.case_state == CaseState.EMERGENCY_HOLD.value
    finally:
        if handle is not None:
            with suppress(Exception):
                await handle.terminate("test cleanup")
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)


async def _run_emergency_hold_forbidden_transition() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = _new_id("CASE-EMERG-HOLD-FORBID")
    _seed_case(case_id)

    client = await _connect_temporal_with_retry()
    settings = get_settings()

    executor = ThreadPoolExecutor(max_workers=10)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PermitCaseWorkflow],
        activities=[
            ensure_permit_case_exists,
            fetch_permit_case_state,
            apply_state_transition,
            validate_emergency_artifact,
            validate_reviewer_confirmation,
        ],
        activity_executor=executor,
    )

    worker_task = asyncio.create_task(worker.run())
    handle = None
    try:
        workflow_id = permit_case_workflow_id(case_id)
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            PermitCaseWorkflowInput(case_id=case_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        run_id = handle.first_execution_run_id or handle.run_id
        assert run_id is not None

        await _wait_for_initial_review_denial(workflow_id, run_id)

        emergency_id = await _declare_emergency(case_id)
        await handle.signal("EmergencyHoldEntry", EmergencyHoldRequest(emergency_id=emergency_id))

        entry_request_id = _transition_request_id(
            workflow_id=workflow_id,
            run_id=run_id,
            transition="emergency_hold_entry",
            attempt=1,
        )
        await _wait_for_ledger_row(entry_request_id)

        request_id = _transition_request_id(
            workflow_id=workflow_id,
            run_id=run_id,
            transition="emergency_hold_forbidden",
            attempt=1,
        )
        requested_at = dt.datetime.now(dt.UTC)
        result = apply_state_transition(
            StateTransitionRequest(
                request_id=request_id,
                case_id=case_id,
                from_state=CaseState.EMERGENCY_HOLD,
                to_state=CaseState.SUBMITTED,
                actor_type=ActorType.system_guard,
                actor_id="system-guard",
                correlation_id=f"{workflow_id}:{run_id}",
                causation_id=str(uuid.uuid4()),
                required_review_id=None,
                required_evidence_ids=[],
                override_id=None,
                requested_at=requested_at,
                notes="forbidden direct transition",
            )
        )

        assert isinstance(result, DeniedStateTransitionResult)
        assert result.event_type == "STATE_TRANSITION_DENIED"
        assert result.denial_reason == "FORBIDDEN_TRANSITION"

        row = await _wait_for_ledger_row(request_id)
        assert row.event_type == "STATE_TRANSITION_DENIED"
        assert row.from_state == CaseState.EMERGENCY_HOLD.value
        assert row.to_state == CaseState.SUBMITTED.value
        assert row.correlation_id == f"{workflow_id}:{run_id}"

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            case = session.get(PermitCase, case_id)
            assert case is not None
            assert case.case_state == CaseState.EMERGENCY_HOLD.value

            submitted_change = (
                session.query(CaseTransitionLedger)
                .filter(
                    CaseTransitionLedger.case_id == case_id,
                    CaseTransitionLedger.to_state == CaseState.SUBMITTED.value,
                    CaseTransitionLedger.event_type == "CASE_STATE_CHANGED",
                )
                .count()
            )
            assert submitted_change == 0
    finally:
        if handle is not None:
            with suppress(Exception):
                await handle.terminate("test cleanup")
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)


async def _run_emergency_hold_exit() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = _new_id("CASE-EMERG-HOLD-EXIT")
    _seed_case(case_id)

    decision_id = _new_id("DEC-EMERG-HOLD-EXIT")
    await _create_review_decision(case_id, decision_id)

    client = await _connect_temporal_with_retry()
    settings = get_settings()

    executor = ThreadPoolExecutor(max_workers=10)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PermitCaseWorkflow],
        activities=[
            ensure_permit_case_exists,
            fetch_permit_case_state,
            apply_state_transition,
            validate_emergency_artifact,
            validate_reviewer_confirmation,
        ],
        activity_executor=executor,
    )

    worker_task = asyncio.create_task(worker.run())
    handle = None
    try:
        workflow_id = permit_case_workflow_id(case_id)
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            PermitCaseWorkflowInput(case_id=case_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        run_id = handle.first_execution_run_id or handle.run_id
        assert run_id is not None

        await _wait_for_initial_review_denial(workflow_id, run_id)

        emergency_id = await _declare_emergency(case_id)
        await handle.signal("EmergencyHoldEntry", EmergencyHoldRequest(emergency_id=emergency_id))

        entry_request_id = _transition_request_id(
            workflow_id=workflow_id,
            run_id=run_id,
            transition="emergency_hold_entry",
            attempt=1,
        )
        await _wait_for_ledger_row(entry_request_id)

        await handle.signal(
            "EmergencyHoldExit",
            EmergencyHoldExitRequest(
                target_state=CaseState.REVIEW_PENDING,
                reviewer_confirmation_id=decision_id,
            ),
        )

        exit_request_id = _transition_request_id(
            workflow_id=workflow_id,
            run_id=run_id,
            transition="emergency_hold_exit",
            attempt=1,
        )
        row = await _wait_for_ledger_row(exit_request_id)
        assert row.event_type == "CASE_STATE_CHANGED"
        assert row.from_state == CaseState.EMERGENCY_HOLD.value
        assert row.to_state == CaseState.REVIEW_PENDING.value
        assert row.correlation_id == f"{workflow_id}:{run_id}"

        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            case = session.get(PermitCase, case_id)
            assert case is not None
            assert case.case_state == CaseState.REVIEW_PENDING.value
    finally:
        if handle is not None:
            with suppress(Exception):
                await handle.terminate("test cleanup")
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        executor.shutdown(wait=True, cancel_futures=True)
