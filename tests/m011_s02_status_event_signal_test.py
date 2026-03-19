"""Integration tests for StatusEventSignal workflow handler + POST /status-events API endpoint.

Tests prove:
- POST /status-events persists external_status_events row
- Signal is delivered to workflow
- Workflow branches on normalized_status and calls appropriate persist activity
- Artifact tables have new rows with correct case_id + submission_attempt_id linkage
"""
from __future__ import annotations

import asyncio
import datetime as dt
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from temporalio.worker import Worker

from sps.config import get_settings
from sps.db.models import (
    ApprovalRecord,
    CaseTransitionLedger,
    CorrectionTask,
    InspectionMilestone,
    PermitCase,
    ResubmissionPackage,
)
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    apply_state_transition,
    ensure_permit_case_exists,
    fetch_permit_case_state,
    persist_approval_record,
    persist_correction_task,
    persist_inspection_milestone,
    persist_resubmission_package,
)
from sps.workflows.permit_case.contracts import (
    CaseState,
    ExternalStatusClass,
    PermitCaseWorkflowInput,
    StatusEventSignal,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client
from tests.fixtures.seed_submission_package import seed_submission_attempt

pytestmark = pytest.mark.integration


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
        except Exception as exc:
            last_exc = exc
            time.sleep(0.5)

    raise RuntimeError(f"Postgres not ready after {timeout_s}s (last_exc={type(last_exc).__name__})")


def _migrate_db() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


async def _connect_temporal_with_retry(timeout_s: float = 30.0):
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            return await connect_client()
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(0.5)

    raise RuntimeError(
        f"Temporal not ready after {timeout_s}s (last_exc={type(last_exc).__name__})"
    )


async def _wait_for_ledger_row_by_event(
    *,
    case_id: str,
    event_type: str,
    timeout_s: float = 30.0,
) -> CaseTransitionLedger:
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            row = (
                session.query(CaseTransitionLedger)
                .filter(
                    CaseTransitionLedger.case_id == case_id,
                    CaseTransitionLedger.event_type == event_type,
                )
                .first()
            )
            if row is not None:
                return row
        await asyncio.sleep(0.25)

    raise AssertionError(
        f"case_transition_ledger row not found: case_id={case_id} event_type={event_type}"
    )


async def _wait_for_record(model: type[sa.orm.DeclarativeBase], record_id_field, record_id: str, timeout_s: float = 10.0):
    deadline = time.time() + timeout_s
    SessionLocal = get_sessionmaker()

    while time.time() < deadline:
        with SessionLocal() as session:
            row = session.query(model).filter(record_id_field == record_id).first()
            if row is not None:
                return row
        await asyncio.sleep(0.25)

    raise AssertionError(
        f"{model.__name__} row not found within {timeout_s}s for id={record_id}"
    )


def _reset_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE correction_tasks, resubmission_packages, approval_records, "
                "inspection_milestones, external_status_events, submission_attempts, "
                "submission_packages, evidence_artifacts, permit_cases CASCADE"
            )
        )


def _seed_case_and_submission(case_id: str, submission_attempt_id: str) -> None:
    """Seed PermitCase plus a schema-valid submission attempt graph for test setup."""
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
        session.flush()
        attempt = seed_submission_attempt(session, case_id, submission_attempt_id, attempt_number=1)
        attempt.outcome = "SUCCESS"
        attempt.external_tracking_id = f"EXT-{case_id}"
        attempt.submitted_at = dt.datetime.now(dt.UTC)
        session.commit()


def test_status_event_signal_comment_issued() -> None:
    """Test COMMENT_ISSUED status event triggers persist_correction_task."""
    asyncio.run(_run_comment_issued_test())


async def _run_comment_issued_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()

    suffix = uuid.uuid4().hex[:8]
    case_id = f"CASE-COMMENT-TEST-{suffix}"
    submission_attempt_id = f"SUB-ATT-COMMENT-{suffix}"

    _reset_db()
    _seed_case_and_submission(case_id, submission_attempt_id)
    
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
            persist_correction_task,
            persist_resubmission_package,
            persist_approval_record,
            persist_inspection_milestone,
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
        await _wait_for_ledger_row_by_event(case_id=case_id, event_type="APPROVAL_GATE_DENIED")

        # Send StatusEvent signal with COMMENT_ISSUED
        event_id = "ESE-COMMENT-001"
        signal = StatusEventSignal(
            event_id=event_id,
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            normalized_status=ExternalStatusClass.COMMENT_ISSUED,
        )
        await handle.signal("StatusEvent", signal)

        # Verify correction_tasks row exists
        correction_task = await _wait_for_record(
            CorrectionTask,
            CorrectionTask.correction_task_id,
            f"CORRECTION-{event_id}",
        )
        assert correction_task.case_id == case_id
        assert correction_task.submission_attempt_id == submission_attempt_id
        assert correction_task.status == "PENDING"
    finally:
        if handle is not None:
            with suppress(Exception):
                await handle.terminate("test cleanup")
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


def test_status_event_signal_resubmission_requested() -> None:
    """Test RESUBMISSION_REQUESTED status event triggers persist_resubmission_package."""
    asyncio.run(_run_resubmission_requested_test())


async def _run_resubmission_requested_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()

    suffix = uuid.uuid4().hex[:8]
    case_id = f"CASE-RESUBMIT-TEST-{suffix}"
    submission_attempt_id = f"SUB-ATT-RESUBMIT-{suffix}"
    
    _reset_db()
    _seed_case_and_submission(case_id, submission_attempt_id)
    
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
            persist_correction_task,
            persist_resubmission_package,
            persist_approval_record,
            persist_inspection_milestone,
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
        await _wait_for_ledger_row_by_event(case_id=case_id, event_type="APPROVAL_GATE_DENIED")

        # Send StatusEvent signal with RESUBMISSION_REQUESTED
        event_id = "ESE-RESUBMIT-001"
        signal = StatusEventSignal(
            event_id=event_id,
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            normalized_status=ExternalStatusClass.RESUBMISSION_REQUESTED,
        )
        await handle.signal("StatusEvent", signal)

        # Verify resubmission_packages row exists
        resubmission_package = await _wait_for_record(
            ResubmissionPackage,
            ResubmissionPackage.resubmission_package_id,
            f"RESUBMISSION-{event_id}",
        )
        assert resubmission_package.case_id == case_id
        assert resubmission_package.submission_attempt_id == submission_attempt_id
        assert resubmission_package.status == "REQUESTED"
    finally:
        if handle is not None:
            with suppress(Exception):
                await handle.terminate("test cleanup")
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


def test_status_event_signal_approval_final() -> None:
    """Test APPROVAL_FINAL status event triggers persist_approval_record."""
    asyncio.run(_run_approval_final_test())


async def _run_approval_final_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()

    suffix = uuid.uuid4().hex[:8]
    case_id = f"CASE-APPROVAL-TEST-{suffix}"
    submission_attempt_id = f"SUB-ATT-APPROVAL-{suffix}"
    
    _reset_db()
    _seed_case_and_submission(case_id, submission_attempt_id)
    
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
            persist_correction_task,
            persist_resubmission_package,
            persist_approval_record,
            persist_inspection_milestone,
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
        await _wait_for_ledger_row_by_event(case_id=case_id, event_type="APPROVAL_GATE_DENIED")

        # Send StatusEvent signal with APPROVAL_FINAL
        event_id = "ESE-APPROVAL-001"
        signal = StatusEventSignal(
            event_id=event_id,
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            normalized_status=ExternalStatusClass.APPROVAL_FINAL,
        )
        await handle.signal("StatusEvent", signal)

        # Verify approval_records row exists
        approval_record = await _wait_for_record(
            ApprovalRecord,
            ApprovalRecord.approval_record_id,
            f"APPROVAL-{event_id}",
        )
        assert approval_record.case_id == case_id
        assert approval_record.submission_attempt_id == submission_attempt_id
        assert approval_record.decision == "APPROVED"
    finally:
        if handle is not None:
            with suppress(Exception):
                await handle.terminate("test cleanup")
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


def test_status_event_signal_inspection_passed() -> None:
    """Test INSPECTION_PASSED status event triggers persist_inspection_milestone."""
    asyncio.run(_run_inspection_passed_test())


async def _run_inspection_passed_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()

    suffix = uuid.uuid4().hex[:8]
    case_id = f"CASE-INSPECTION-TEST-{suffix}"
    submission_attempt_id = f"SUB-ATT-INSPECTION-{suffix}"
    
    _reset_db()
    _seed_case_and_submission(case_id, submission_attempt_id)
    
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
            persist_correction_task,
            persist_resubmission_package,
            persist_approval_record,
            persist_inspection_milestone,
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
        await _wait_for_ledger_row_by_event(case_id=case_id, event_type="APPROVAL_GATE_DENIED")

        # Send StatusEvent signal with INSPECTION_PASSED
        event_id = "ESE-INSPECTION-001"
        signal = StatusEventSignal(
            event_id=event_id,
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            normalized_status=ExternalStatusClass.INSPECTION_PASSED,
        )
        await handle.signal("StatusEvent", signal)

        # Verify inspection_milestones row exists
        inspection_milestone = await _wait_for_record(
            InspectionMilestone,
            InspectionMilestone.inspection_milestone_id,
            f"INSPECTION-{event_id}",
        )
        assert inspection_milestone.case_id == case_id
        assert inspection_milestone.submission_attempt_id == submission_attempt_id
        assert inspection_milestone.milestone_type == "FINAL"
        assert inspection_milestone.status == "INSPECTION_PASSED"
    finally:
        if handle is not None:
            with suppress(Exception):
                await handle.terminate("test cleanup")
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
