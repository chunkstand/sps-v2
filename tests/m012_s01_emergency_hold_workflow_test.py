from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress

import pytest
import sqlalchemy as sa
import ulid
from alembic import command
from alembic.config import Config
from temporalio.api.enums.v1.workflow_pb2 import WorkflowExecutionStatus
from temporalio.worker import Worker

from sps.config import get_settings
from sps.db.models import CaseTransitionLedger, EmergencyRecord, PermitCase, ReviewDecision
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    validate_emergency_artifact,
    validate_reviewer_confirmation,
)
from sps.workflows.permit_case.contracts import (
    CaseState,
    EmergencyHoldExitRequest,
    EmergencyHoldRequest,
    PermitCaseWorkflowInput,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client

if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Temporal integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


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


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _capture_workflow_logs() -> _ListHandler:
    module_logger = logging.getLogger("sps.workflows.permit_case.workflow")
    module_logger.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = _ListHandler()
    module_logger.addHandler(handler)
    root_logger.addHandler(handler)
    return handler


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


async def _wait_for_workflow_status(
    handle,
    *,
    expected_status: WorkflowExecutionStatus,
    timeout_s: float = 10.0,
) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        desc = await handle.describe()
        if desc.status == expected_status:
            return
        await asyncio.sleep(0.5)

    raise AssertionError(
        f"workflow did not reach status={expected_status} within {timeout_s}s (last={desc.status})"
    )


def _seed_case(case_id: str, *, state: CaseState = CaseState.REVIEW_PENDING) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        case = PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=state.value,
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


def _seed_emergency(case_id: str, emergency_id: str, *, expires_at: dt.datetime) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        record = EmergencyRecord(
            emergency_id=emergency_id,
            incident_id=f"INC-{emergency_id}",
            case_id=case_id,
            scope="FULL_CASE",
            declared_by="operator-1",
            started_at=dt.datetime.now(dt.UTC),
            expires_at=expires_at,
            allowed_bypasses=None,
            forbidden_bypasses=None,
            cleanup_due_at=None,
        )
        session.add(record)
        session.commit()


def _seed_review_decision(case_id: str, decision_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        decision = ReviewDecision(
            decision_id=decision_id,
            schema_version="1.0.0",
            case_id=case_id,
            object_type="PermitCase",
            object_id=case_id,
            decision_outcome="ACCEPT",
            reviewer_id="reviewer-1",
            subject_author_id=None,
            reviewer_independence_status="PASS",
            evidence_ids=[],
            contradiction_resolution=None,
            dissent_flag=False,
            notes=None,
            decision_at=dt.datetime.now(dt.UTC),
            idempotency_key=f"decision/{decision_id}",
        )
        session.add(decision)
        session.commit()


def test_emergency_hold_entry_with_valid_emergency() -> None:
    handler = _capture_workflow_logs()
    try:
        asyncio.run(_run_emergency_hold_entry_success(handler))
    finally:
        logging.getLogger("sps.workflows.permit_case.workflow").removeHandler(handler)
        logging.getLogger().removeHandler(handler)


async def _run_emergency_hold_entry_success(handler: _ListHandler) -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = _new_id("CASE-EMERG-HOLD-ENTRY")
    emergency_id = _new_id("EMERG-ENTRY")
    _seed_case(case_id)
    _seed_emergency(case_id, emergency_id, expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(hours=2))

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

        await handle.signal(
            "EmergencyHoldEntry",
            EmergencyHoldRequest(emergency_id=emergency_id),
        )

        entry_request_id = _transition_request_id(
            workflow_id=workflow_id,
            run_id=run_id,
            transition="emergency_hold_entry",
            attempt=1,
        )
        row = await _wait_for_ledger_row(entry_request_id)
        assert row.event_type == "CASE_STATE_CHANGED"
        assert row.to_state == CaseState.EMERGENCY_HOLD.value

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


def test_emergency_hold_entry_with_expired_emergency_raises() -> None:
    asyncio.run(_run_emergency_hold_entry_expired())


async def _run_emergency_hold_entry_expired() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = _new_id("CASE-EMERG-HOLD-ENTRY-EXPIRED")
    emergency_id = _new_id("EMERG-ENTRY-EXPIRED")
    _seed_case(case_id)
    _seed_emergency(case_id, emergency_id, expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1))

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

        await handle.signal(
            "EmergencyHoldEntry",
            EmergencyHoldRequest(emergency_id=emergency_id),
        )

        await _wait_for_workflow_status(
            handle,
            expected_status=WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_FAILED,
        )

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


def test_emergency_hold_exit_with_reviewer_confirmation() -> None:
    handler = _capture_workflow_logs()
    try:
        asyncio.run(_run_emergency_hold_exit_success(handler))
    finally:
        logging.getLogger("sps.workflows.permit_case.workflow").removeHandler(handler)
        logging.getLogger().removeHandler(handler)


async def _run_emergency_hold_exit_success(handler: _ListHandler) -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = _new_id("CASE-EMERG-HOLD-EXIT")
    emergency_id = _new_id("EMERG-EXIT")
    decision_id = _new_id("DECISION-EXIT")
    _seed_case(case_id)
    _seed_emergency(case_id, emergency_id, expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(hours=2))
    _seed_review_decision(case_id, decision_id)

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

        await handle.signal(
            "EmergencyHoldEntry",
            EmergencyHoldRequest(emergency_id=emergency_id),
        )
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
        exit_row = await _wait_for_ledger_row(exit_request_id)
        assert exit_row.event_type == "CASE_STATE_CHANGED"
        assert exit_row.from_state == CaseState.EMERGENCY_HOLD.value
        assert exit_row.to_state == CaseState.REVIEW_PENDING.value

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


def test_emergency_hold_exit_without_confirmation_raises() -> None:
    asyncio.run(_run_emergency_hold_exit_missing_confirmation())


async def _run_emergency_hold_exit_missing_confirmation() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = _new_id("CASE-EMERG-HOLD-EXIT-MISSING")
    emergency_id = _new_id("EMERG-EXIT-MISSING")
    _seed_case(case_id)
    _seed_emergency(case_id, emergency_id, expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(hours=2))

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

        await handle.signal(
            "EmergencyHoldEntry",
            EmergencyHoldRequest(emergency_id=emergency_id),
        )
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
                reviewer_confirmation_id=_new_id("DECISION-MISSING"),
            ),
        )

        await _wait_for_workflow_status(
            handle,
            expected_status=WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_FAILED,
        )

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
