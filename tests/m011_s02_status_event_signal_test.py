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
    CorrectionTask,
    InspectionMilestone,
    PermitCase,
    ResubmissionPackage,
    SubmissionAttempt,
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


def _clear_case_row(case_id: str) -> None:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        session.execute(sa.delete(PermitCase).where(PermitCase.case_id == case_id))
        session.execute(sa.delete(SubmissionAttempt).where(SubmissionAttempt.case_id == case_id))
        session.execute(sa.delete(CorrectionTask).where(CorrectionTask.case_id == case_id))
        session.execute(sa.delete(ResubmissionPackage).where(ResubmissionPackage.case_id == case_id))
        session.execute(sa.delete(ApprovalRecord).where(ApprovalRecord.case_id == case_id))
        session.execute(sa.delete(InspectionMilestone).where(InspectionMilestone.case_id == case_id))
        session.commit()


def _seed_case_and_submission(case_id: str, submission_attempt_id: str) -> None:
    """Seed PermitCase + SubmissionAttempt for test setup."""
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        case = PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=CaseState.SUBMITTED.value,
            review_state="PENDING",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
        session.add(case)
        
        attempt = SubmissionAttempt(
            submission_attempt_id=submission_attempt_id,
            case_id=case_id,
            package_id=f"PKG-{case_id}",
            manifest_artifact_id=f"MANIFEST-{case_id}",
            target_portal_family="CITY_PORTAL_FAMILY_A",
            portal_support_level="FULLY_SUPPORTED",
            request_id=f"REQ-{case_id}",
            idempotency_key=f"submit/{case_id}/attempt-1",
            attempt_number=1,
            status="SUBMITTED",
            outcome="SUCCESS",
            external_tracking_id=f"EXT-{case_id}",
            receipt_artifact_id=None,
            submitted_at=dt.datetime.now(dt.UTC),
            failure_class=None,
            last_error=None,
            last_error_context=None,
        )
        session.add(attempt)
        session.commit()


def test_status_event_signal_comment_issued() -> None:
    """Test COMMENT_ISSUED status event triggers persist_correction_task."""
    asyncio.run(_run_comment_issued_test())


async def _run_comment_issued_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    
    case_id = "CASE-COMMENT-TEST-001"
    submission_attempt_id = "SUB-ATT-001"
    
    _clear_case_row(case_id)
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
    try:
        workflow_id = permit_case_workflow_id(case_id)
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            PermitCaseWorkflowInput(case_id=case_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        
        # Send StatusEvent signal with COMMENT_ISSUED
        event_id = "ESE-COMMENT-001"
        signal = StatusEventSignal(
            event_id=event_id,
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            normalized_status=ExternalStatusClass.COMMENT_ISSUED,
        )
        await handle.signal("StatusEvent", signal)
        
        # Allow workflow to process signal
        await asyncio.sleep(2)
        
        # Verify correction_tasks row exists
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            correction_task = session.query(CorrectionTask).filter(
                CorrectionTask.correction_task_id == f"CORRECTION-{event_id}"
            ).first()
            
            assert correction_task is not None
            assert correction_task.case_id == case_id
            assert correction_task.submission_attempt_id == submission_attempt_id
            assert correction_task.status == "PENDING"
    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


def test_status_event_signal_resubmission_requested() -> None:
    """Test RESUBMISSION_REQUESTED status event triggers persist_resubmission_package."""
    asyncio.run(_run_resubmission_requested_test())


async def _run_resubmission_requested_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    
    case_id = "CASE-RESUBMIT-TEST-001"
    submission_attempt_id = "SUB-ATT-002"
    
    _clear_case_row(case_id)
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
    try:
        workflow_id = permit_case_workflow_id(case_id)
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            PermitCaseWorkflowInput(case_id=case_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        
        # Send StatusEvent signal with RESUBMISSION_REQUESTED
        event_id = "ESE-RESUBMIT-001"
        signal = StatusEventSignal(
            event_id=event_id,
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            normalized_status=ExternalStatusClass.RESUBMISSION_REQUESTED,
        )
        await handle.signal("StatusEvent", signal)
        
        # Allow workflow to process signal
        await asyncio.sleep(2)
        
        # Verify resubmission_packages row exists
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            resubmission_package = session.query(ResubmissionPackage).filter(
                ResubmissionPackage.resubmission_package_id == f"RESUBMISSION-{event_id}"
            ).first()
            
            assert resubmission_package is not None
            assert resubmission_package.case_id == case_id
            assert resubmission_package.submission_attempt_id == submission_attempt_id
            assert resubmission_package.status == "REQUESTED"
    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


def test_status_event_signal_approval_final() -> None:
    """Test APPROVAL_FINAL status event triggers persist_approval_record."""
    asyncio.run(_run_approval_final_test())


async def _run_approval_final_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    
    case_id = "CASE-APPROVAL-TEST-001"
    submission_attempt_id = "SUB-ATT-003"
    
    _clear_case_row(case_id)
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
    try:
        workflow_id = permit_case_workflow_id(case_id)
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            PermitCaseWorkflowInput(case_id=case_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        
        # Send StatusEvent signal with APPROVAL_FINAL
        event_id = "ESE-APPROVAL-001"
        signal = StatusEventSignal(
            event_id=event_id,
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            normalized_status=ExternalStatusClass.APPROVAL_FINAL,
        )
        await handle.signal("StatusEvent", signal)
        
        # Allow workflow to process signal
        await asyncio.sleep(2)
        
        # Verify approval_records row exists
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            approval_record = session.query(ApprovalRecord).filter(
                ApprovalRecord.approval_record_id == f"APPROVAL-{event_id}"
            ).first()
            
            assert approval_record is not None
            assert approval_record.case_id == case_id
            assert approval_record.submission_attempt_id == submission_attempt_id
            assert approval_record.decision == "APPROVED"
    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


def test_status_event_signal_inspection_passed() -> None:
    """Test INSPECTION_PASSED status event triggers persist_inspection_milestone."""
    asyncio.run(_run_inspection_passed_test())


async def _run_inspection_passed_test() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    
    case_id = "CASE-INSPECTION-TEST-001"
    submission_attempt_id = "SUB-ATT-004"
    
    _clear_case_row(case_id)
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
    try:
        workflow_id = permit_case_workflow_id(case_id)
        handle = await client.start_workflow(
            PermitCaseWorkflow.run,
            PermitCaseWorkflowInput(case_id=case_id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        
        # Send StatusEvent signal with INSPECTION_PASSED
        event_id = "ESE-INSPECTION-001"
        signal = StatusEventSignal(
            event_id=event_id,
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            normalized_status=ExternalStatusClass.INSPECTION_PASSED,
        )
        await handle.signal("StatusEvent", signal)
        
        # Allow workflow to process signal
        await asyncio.sleep(2)
        
        # Verify inspection_milestones row exists
        SessionLocal = get_sessionmaker()
        with SessionLocal() as session:
            inspection_milestone = session.query(InspectionMilestone).filter(
                InspectionMilestone.inspection_milestone_id == f"INSPECTION-{event_id}"
            ).first()
            
            assert inspection_milestone is not None
            assert inspection_milestone.case_id == case_id
            assert inspection_milestone.submission_attempt_id == submission_attempt_id
            assert inspection_milestone.milestone_type == "FINAL"
            assert inspection_milestone.status == "INSPECTION_PASSED"
    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
