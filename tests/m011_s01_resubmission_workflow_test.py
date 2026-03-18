"""Temporal integration tests for post-submission resubmission loop workflow.

Validates that PermitCaseWorkflow handles comment → correction → resubmission → submitted
transitions with durable artifact persistence and state transitions.
"""

from __future__ import annotations

import datetime as dt
import os
import time
import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session
from temporalio.client import Client
from temporalio.worker import Worker

from sps.db.models import (
    ApprovalRecord,
    CaseTransitionLedger,
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
    persist_compliance_evaluation,
    persist_correction_task,
    persist_incentive_assessment,
    persist_inspection_milestone,
    persist_jurisdiction_resolutions,
    persist_requirement_sets,
    persist_resubmission_package,
    persist_submission_package,
)
from sps.workflows.permit_case.contracts import (
    CaseState,
    PermitCaseWorkflowInput,
    PersistApprovalRecordRequest,
    PersistCorrectionTaskRequest,
    PersistInspectionMilestoneRequest,
    PersistResubmissionPackageRequest,
)
from sps.workflows.permit_case.workflow import PermitCaseWorkflow


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


@pytest.fixture(scope="session", autouse=True)
def _migrate_db() -> None:
    _wait_for_postgres_ready()
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture
def db_session() -> Session:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE TABLE correction_tasks, resubmission_packages, approval_records, "
                "inspection_milestones, case_transition_ledger, submission_attempts, "
                "submission_packages, document_artifacts, permit_cases, evidence_artifacts CASCADE"
            )
        )

    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
async def temporal_client():
    """Connect to local Temporal server for integration tests."""
    client = await Client.connect("localhost:7233")
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
async def temporal_worker(temporal_client):
    """Start Temporal worker with permit case workflow + activities."""
    
    worker = Worker(
        temporal_client,
        task_queue="permit-case-test",
        workflows=[PermitCaseWorkflow],
        activities=[
            ensure_permit_case_exists,
            fetch_permit_case_state,
            apply_state_transition,
            persist_jurisdiction_resolutions,
            persist_requirement_sets,
            persist_compliance_evaluation,
            persist_incentive_assessment,
            persist_submission_package,
            persist_correction_task,
            persist_resubmission_package,
            persist_approval_record,
            persist_inspection_milestone,
        ],
    )
    
    async with worker:
        yield worker


@pytest.mark.integration
@pytest.mark.asyncio
async def test_comment_review_to_correction_pending_transition(
    db_session, temporal_client, temporal_worker
):
    """Workflow transitions COMMENT_REVIEW_PENDING → CORRECTION_PENDING."""
    
    case_id = f"case-comment-{uuid.uuid4().hex[:8]}"
    workflow_id = f"wf-comment-{uuid.uuid4().hex[:8]}"
    
    # Setup: Create case in COMMENT_REVIEW_PENDING state
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=CaseState.COMMENT_REVIEW_PENDING.value,
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            legal_hold=False,
        )
    )
    db_session.commit()
    
    # Act: Start workflow
    handle = await temporal_client.start_workflow(
        PermitCaseWorkflow.run,
        PermitCaseWorkflowInput(case_id=case_id),
        id=workflow_id,
        task_queue="permit-case-test",
    )
    
    result = await handle.result()
    
    # Assert: Workflow transitioned to CORRECTION_PENDING
    assert result.case_id == case_id
    assert result.final_result is not None
    assert result.final_result.result == "applied"
    
    db_session.expire_all()
    case = db_session.get(PermitCase, case_id)
    assert case.case_state == CaseState.CORRECTION_PENDING.value
    
    # Verify transition ledger entry
    transitions = (
        db_session.query(CaseTransitionLedger)
        .filter(CaseTransitionLedger.case_id == case_id)
        .all()
    )
    assert len(transitions) == 1
    assert transitions[0].from_state == CaseState.COMMENT_REVIEW_PENDING.value
    assert transitions[0].to_state == CaseState.CORRECTION_PENDING.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resubmission_pending_to_document_complete_transition(
    db_session, temporal_client, temporal_worker
):
    """Workflow transitions RESUBMISSION_PENDING → DOCUMENT_COMPLETE and regenerates package."""
    
    case_id = f"case-resub-{uuid.uuid4().hex[:8]}"
    workflow_id = f"wf-resub-{uuid.uuid4().hex[:8]}"
    
    # Setup: Create case in RESUBMISSION_PENDING state
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=CaseState.RESUBMISSION_PENDING.value,
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            legal_hold=False,
        )
    )
    db_session.commit()
    
    # Act: Start workflow
    handle = await temporal_client.start_workflow(
        PermitCaseWorkflow.run,
        PermitCaseWorkflowInput(case_id=case_id),
        id=workflow_id,
        task_queue="permit-case-test",
    )
    
    result = await handle.result()
    
    # Assert: Workflow transitioned to DOCUMENT_COMPLETE, created package, and submitted
    assert result.case_id == case_id
    
    db_session.expire_all()
    case = db_session.get(PermitCase, case_id)
    # Should end in SUBMITTED or MANUAL_SUBMISSION_REQUIRED depending on portal support
    assert case.case_state in [
        CaseState.SUBMITTED.value,
        CaseState.MANUAL_SUBMISSION_REQUIRED.value,
    ]
    
    # Verify resubmission path: RESUBMISSION_PENDING → DOCUMENT_COMPLETE → SUBMITTED
    transitions = (
        db_session.query(CaseTransitionLedger)
        .filter(CaseTransitionLedger.case_id == case_id)
        .order_by(CaseTransitionLedger.occurred_at)
        .all()
    )
    assert len(transitions) >= 2
    assert transitions[0].from_state == CaseState.RESUBMISSION_PENDING.value
    assert transitions[0].to_state == CaseState.DOCUMENT_COMPLETE.value
    assert transitions[1].from_state == CaseState.DOCUMENT_COMPLETE.value
    assert transitions[1].to_state in [
        CaseState.SUBMITTED.value,
        CaseState.MANUAL_SUBMISSION_REQUIRED.value,
    ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_correction_task_persistence_from_workflow(
    db_session, temporal_client, temporal_worker
):
    """Correction task artifacts are persisted and queryable."""
    
    case_id = f"case-correction-{uuid.uuid4().hex[:8]}"
    attempt_id = f"attempt-{uuid.uuid4().hex[:8]}"
    correction_task_id = f"correction-{uuid.uuid4().hex[:8]}"
    
    # Setup: Case and attempt
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=CaseState.SUBMITTED.value,
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            legal_hold=False,
        )
    )
    db_session.add(
        SubmissionAttempt(
            submission_attempt_id=attempt_id,
            case_id=case_id,
            attempt_number=1,
            status="SUBMITTED",
            submission_mode="AUTOMATED",
        )
    )
    db_session.commit()
    
    # Act: Persist correction task via activity directly
    request = PersistCorrectionTaskRequest(
        correction_task_id=correction_task_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        status="PENDING",
        summary="Revise site plan per comment #3",
        requested_at=dt.datetime(2026, 3, 16, 12, 0, 0, tzinfo=dt.UTC),
        due_at=dt.datetime(2026, 3, 23, 12, 0, 0, tzinfo=dt.UTC),
    )
    
    result_id = persist_correction_task(request)
    assert result_id == correction_task_id
    
    # Assert: Task queryable
    db_session.expire_all()
    task = db_session.get(CorrectionTask, correction_task_id)
    assert task is not None
    assert task.case_id == case_id
    assert task.submission_attempt_id == attempt_id
    assert task.status == "PENDING"
    assert task.summary == "Revise site plan per comment #3"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resubmission_package_persistence_from_workflow(
    db_session, temporal_client, temporal_worker
):
    """Resubmission package artifacts are persisted and queryable."""
    
    case_id = f"case-resub-pkg-{uuid.uuid4().hex[:8]}"
    attempt_id = f"attempt-{uuid.uuid4().hex[:8]}"
    resubmission_package_id = f"resub-pkg-{uuid.uuid4().hex[:8]}"
    
    # Setup: Case and attempt
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=CaseState.RESUBMISSION_PENDING.value,
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            legal_hold=False,
        )
    )
    db_session.add(
        SubmissionAttempt(
            submission_attempt_id=attempt_id,
            case_id=case_id,
            attempt_number=2,
            status="PENDING",
            submission_mode="AUTOMATED",
        )
    )
    db_session.commit()
    
    # Act: Persist resubmission package
    request = PersistResubmissionPackageRequest(
        resubmission_package_id=resubmission_package_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        package_id="pkg-v2",
        package_version="2.0.0",
        status="PREPARED",
        submitted_at=dt.datetime(2026, 3, 16, 14, 0, 0, tzinfo=dt.UTC),
    )
    
    result_id = persist_resubmission_package(request)
    assert result_id == resubmission_package_id
    
    # Assert: Package queryable
    db_session.expire_all()
    pkg = db_session.get(ResubmissionPackage, resubmission_package_id)
    assert pkg is not None
    assert pkg.case_id == case_id
    assert pkg.submission_attempt_id == attempt_id
    assert pkg.package_id == "pkg-v2"
    assert pkg.status == "PREPARED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_approval_record_persistence_from_workflow(
    db_session, temporal_client, temporal_worker
):
    """Approval record artifacts are persisted and queryable."""
    
    case_id = f"case-approval-{uuid.uuid4().hex[:8]}"
    attempt_id = f"attempt-{uuid.uuid4().hex[:8]}"
    approval_record_id = f"approval-{uuid.uuid4().hex[:8]}"
    
    # Setup: Case and attempt
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=CaseState.SUBMITTED.value,
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            legal_hold=False,
        )
    )
    db_session.add(
        SubmissionAttempt(
            submission_attempt_id=attempt_id,
            case_id=case_id,
            attempt_number=1,
            status="SUBMITTED",
            submission_mode="AUTOMATED",
        )
    )
    db_session.commit()
    
    # Act: Persist approval record
    request = PersistApprovalRecordRequest(
        approval_record_id=approval_record_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        decision="APPROVED",
        authority="City Planning Department",
        decided_at=dt.datetime(2026, 3, 16, 15, 0, 0, tzinfo=dt.UTC),
    )
    
    result_id = persist_approval_record(request)
    assert result_id == approval_record_id
    
    # Assert: Record queryable
    db_session.expire_all()
    record = db_session.get(ApprovalRecord, approval_record_id)
    assert record is not None
    assert record.case_id == case_id
    assert record.decision == "APPROVED"
    assert record.authority == "City Planning Department"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_inspection_milestone_persistence_from_workflow(
    db_session, temporal_client, temporal_worker
):
    """Inspection milestone artifacts are persisted and queryable."""
    
    case_id = f"case-inspection-{uuid.uuid4().hex[:8]}"
    attempt_id = f"attempt-{uuid.uuid4().hex[:8]}"
    inspection_milestone_id = f"inspection-{uuid.uuid4().hex[:8]}"
    
    # Setup: Case and attempt
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state=CaseState.SUBMITTED.value,
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            legal_hold=False,
        )
    )
    db_session.add(
        SubmissionAttempt(
            submission_attempt_id=attempt_id,
            case_id=case_id,
            attempt_number=1,
            status="SUBMITTED",
            submission_mode="AUTOMATED",
        )
    )
    db_session.commit()
    
    # Act: Persist inspection milestone
    request = PersistInspectionMilestoneRequest(
        inspection_milestone_id=inspection_milestone_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        milestone_type="FOUNDATION",
        status="SCHEDULED",
        scheduled_for=dt.datetime(2026, 3, 20, 9, 0, 0, tzinfo=dt.UTC),
    )
    
    result_id = persist_inspection_milestone(request)
    assert result_id == inspection_milestone_id
    
    # Assert: Milestone queryable
    db_session.expire_all()
    milestone = db_session.get(InspectionMilestone, inspection_milestone_id)
    assert milestone is not None
    assert milestone.case_id == case_id
    assert milestone.milestone_type == "FOUNDATION"
    assert milestone.status == "SCHEDULED"
