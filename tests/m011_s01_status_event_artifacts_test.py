"""Integration tests for post-submission artifact persistence from status events.

Validates that correction/resubmission/approval/inspection artifacts are persisted
idempotently from normalized external status events with proper case/submission_attempt linkage.
"""

from __future__ import annotations

import datetime as dt
import os
import time

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from sps.db.models import (
    ApprovalRecord,
    CorrectionTask,
    ExternalStatusEvent,
    InspectionMilestone,
    PermitCase,
    ResubmissionPackage,
)
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    persist_approval_record,
    persist_correction_task,
    persist_external_status_event,
    persist_inspection_milestone,
    persist_resubmission_package,
)
from sps.workflows.permit_case.contracts import (
    ExternalStatusClass,
    ExternalStatusNormalizationRequest,
    PersistApprovalRecordRequest,
    PersistCorrectionTaskRequest,
    PersistInspectionMilestoneRequest,
    PersistResubmissionPackageRequest,
)


if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "DB-backed integration tests are opt-in (set SPS_RUN_TEMPORAL_INTEGRATION=1)",
        allow_module_level=True,
    )


@pytest.fixture(autouse=True)
def _configure_phase7_fixture_override() -> None:
    original_phase7 = os.environ.get("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE")
    os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
    try:
        yield
    finally:
        if original_phase7 is not None:
            os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = original_phase7
        else:
            os.environ.pop("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE", None)


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
                "TRUNCATE TABLE correction_tasks, resubmission_packages, approval_records, inspection_milestones, external_status_events, submission_attempts, permit_cases CASCADE"
            )
        )

    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.integration
def test_persist_correction_task_creates_artifact(db_session, seed_fixtures):
    """Persist correction task artifact with case/submission_attempt linkage validation."""
    
    case_id = "case-correction-001"
    attempt_id = "attempt-correction-001"
    correction_task_id = "correction-task-001"
    
    # Setup: Create case and submission attempt
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state="SUBMITTED",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    seed_fixtures(case_id, attempt_id, attempt_number=1, status="SUBMITTED")
    db_session.commit()
    
    # Act: Persist correction task
    request = PersistCorrectionTaskRequest(
        correction_task_id=correction_task_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        status="PENDING",
        summary="Address zoning setback requirements",
        requested_at=dt.datetime(2026, 3, 16, 12, 0, 0, tzinfo=dt.UTC),
        due_at=dt.datetime(2026, 3, 23, 12, 0, 0, tzinfo=dt.UTC),
    )
    
    result = persist_correction_task(request)
    
    # Assert: Task created
    assert result == correction_task_id
    
    task = db_session.get(CorrectionTask, correction_task_id)
    assert task is not None
    assert task.case_id == case_id
    assert task.submission_attempt_id == attempt_id
    assert task.status == "PENDING"
    assert task.summary == "Address zoning setback requirements"


@pytest.mark.integration
def test_persist_correction_task_idempotent(db_session, seed_fixtures):
    """Persist correction task is idempotent on replay."""
    
    case_id = "case-correction-002"
    attempt_id = "attempt-correction-002"
    correction_task_id = "correction-task-002"
    
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state="SUBMITTED",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    seed_fixtures(case_id, attempt_id, attempt_number=1, status="SUBMITTED")
    db_session.commit()
    
    request = PersistCorrectionTaskRequest(
        correction_task_id=correction_task_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        status="PENDING",
        summary="Fix structural calculations",
    )
    
    # First call
    result1 = persist_correction_task(request)
    assert result1 == correction_task_id
    
    # Second call (idempotent replay)
    result2 = persist_correction_task(request)
    assert result2 == correction_task_id
    
    # Assert: Only one row exists
    tasks = db_session.query(CorrectionTask).filter_by(case_id=case_id).all()
    assert len(tasks) == 1


@pytest.mark.integration
def test_persist_correction_task_validates_case_attempt_linkage(db_session, seed_fixtures):
    """Persist correction task rejects mismatched case/attempt."""
    
    case_id = "case-correction-003"
    other_case_id = "case-correction-other"
    attempt_id = "attempt-correction-003"
    correction_task_id = "correction-task-003"
    
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state="SUBMITTED",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    db_session.add(
        PermitCase(
            case_id=other_case_id,
            tenant_id="tenant-local",
            project_id=f"project-{other_case_id}",
            case_state="SUBMITTED",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    seed_fixtures(other_case_id, attempt_id, attempt_number=1, status="SUBMITTED")
    db_session.commit()
    
    request = PersistCorrectionTaskRequest(
        correction_task_id=correction_task_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,  # Mismatched!
        status="PENDING",
    )
    
    with pytest.raises(LookupError, match="submission_attempt_case_mismatch"):
        persist_correction_task(request)


@pytest.mark.integration
def test_persist_resubmission_package_creates_artifact(db_session, seed_fixtures):
    """Persist resubmission package artifact."""
    
    case_id = "case-resub-001"
    attempt_id = "attempt-resub-001"
    resubmission_package_id = "resub-pkg-001"
    
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state="RESUBMISSION_PENDING",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    seed_fixtures(case_id, attempt_id, attempt_number=2, status="PENDING")
    db_session.commit()
    
    request = PersistResubmissionPackageRequest(
        resubmission_package_id=resubmission_package_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        package_id="pkg-v2",
        package_version="2.0.0",
        status="PREPARED",
        submitted_at=dt.datetime(2026, 3, 16, 14, 0, 0, tzinfo=dt.UTC),
    )
    
    result = persist_resubmission_package(request)
    
    assert result == resubmission_package_id
    
    pkg = db_session.get(ResubmissionPackage, resubmission_package_id)
    assert pkg is not None
    assert pkg.case_id == case_id
    assert pkg.package_id == "pkg-v2"
    assert pkg.package_version == "2.0.0"
    assert pkg.status == "PREPARED"


@pytest.mark.integration
def test_persist_approval_record_creates_artifact(db_session, seed_fixtures):
    """Persist approval record artifact."""
    
    case_id = "case-approval-001"
    attempt_id = "attempt-approval-001"
    approval_record_id = "approval-001"
    
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state="SUBMITTED",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    seed_fixtures(case_id, attempt_id, attempt_number=1, status="SUBMITTED")
    db_session.commit()
    
    request = PersistApprovalRecordRequest(
        approval_record_id=approval_record_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        decision="APPROVED",
        authority="City Planning Department",
        decided_at=dt.datetime(2026, 3, 16, 15, 0, 0, tzinfo=dt.UTC),
    )
    
    result = persist_approval_record(request)
    
    assert result == approval_record_id
    
    record = db_session.get(ApprovalRecord, approval_record_id)
    assert record is not None
    assert record.case_id == case_id
    assert record.decision == "APPROVED"
    assert record.authority == "City Planning Department"


@pytest.mark.integration
def test_persist_inspection_milestone_creates_artifact(db_session, seed_fixtures):
    """Persist inspection milestone artifact."""
    
    case_id = "case-inspection-001"
    attempt_id = "attempt-inspection-001"
    inspection_milestone_id = "inspection-001"
    
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state="SUBMITTED",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    seed_fixtures(case_id, attempt_id, attempt_number=1, status="SUBMITTED")
    db_session.commit()
    
    request = PersistInspectionMilestoneRequest(
        inspection_milestone_id=inspection_milestone_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        milestone_type="FOUNDATION",
        status="SCHEDULED",
        scheduled_for=dt.datetime(2026, 3, 20, 9, 0, 0, tzinfo=dt.UTC),
    )
    
    result = persist_inspection_milestone(request)
    
    assert result == inspection_milestone_id
    
    milestone = db_session.get(InspectionMilestone, inspection_milestone_id)
    assert milestone is not None
    assert milestone.case_id == case_id
    assert milestone.milestone_type == "FOUNDATION"
    assert milestone.status == "SCHEDULED"


@pytest.mark.integration
def test_external_status_normalization_with_new_statuses(db_session, seed_fixtures):
    """External status event normalization handles new post-submission statuses."""
    
    case_id = "case-7-new-statuses"
    attempt_id = "attempt-7-new-statuses"
    event_id = "event-comment-issued"
    
    # Setup: Use case-7 (which maps to CITY_PORTAL_FAMILY_A)
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state="SUBMITTED",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    seed_fixtures(case_id, attempt_id, attempt_number=1, status="SUBMITTED")
    db_session.commit()
    
    # Act: Normalize COMMENT_ISSUED status
    request = ExternalStatusNormalizationRequest(
        event_id=event_id,
        case_id=case_id,
        submission_attempt_id=attempt_id,
        raw_status="Comments Issued",
        received_at=dt.datetime(2026, 3, 16, 10, 0, 0, tzinfo=dt.UTC),
        evidence_ids=["comment_letter"],
    )
    
    result = persist_external_status_event(request)
    
    # Assert: Event persisted with normalized status
    assert result.event_id == event_id
    assert result.normalized_status == ExternalStatusClass.COMMENT_ISSUED
    assert result.confidence.value == "HIGH"
    
    event = db_session.get(ExternalStatusEvent, event_id)
    assert event is not None
    assert event.normalized_status == "COMMENT_ISSUED"
    assert event.raw_status == "Comments Issued"


@pytest.mark.integration
def test_approval_and_inspection_status_normalization(db_session, seed_fixtures):
    """Approval and inspection statuses normalize correctly."""
    
    case_id = "case-7-approval-inspect"
    attempt_id = "attempt-7-approval-inspect"
    
    db_session.add(
        PermitCase(
            case_id=case_id,
            tenant_id="tenant-local",
            project_id=f"project-{case_id}",
            case_state="SUBMITTED",
            review_state="APPROVED",
            submission_mode="AUTOMATED",
            portal_support_level="FULLY_SUPPORTED",
            current_package_id=None,
            current_release_profile="default",
            legal_hold=False,
            closure_reason=None,
        )
    )
    seed_fixtures(case_id, attempt_id, attempt_number=1, status="SUBMITTED")
    db_session.commit()
    
    # Test APPROVAL_FINAL
    request1 = ExternalStatusNormalizationRequest(
        event_id="event-final-approval",
        case_id=case_id,
        submission_attempt_id=attempt_id,
        raw_status="Final Approval",
        received_at=dt.datetime(2026, 3, 16, 11, 0, 0, tzinfo=dt.UTC),
    )
    result1 = persist_external_status_event(request1)
    assert result1.normalized_status == ExternalStatusClass.APPROVAL_FINAL
    
    # Test INSPECTION_SCHEDULED
    request2 = ExternalStatusNormalizationRequest(
        event_id="event-inspection-scheduled",
        case_id=case_id,
        submission_attempt_id=attempt_id,
        raw_status="Inspection Scheduled",
        received_at=dt.datetime(2026, 3, 16, 12, 0, 0, tzinfo=dt.UTC),
    )
    result2 = persist_external_status_event(request2)
    assert result2.normalized_status == ExternalStatusClass.INSPECTION_SCHEDULED
    
    # Test INSPECTION_PASSED
    request3 = ExternalStatusNormalizationRequest(
        event_id="event-inspection-passed",
        case_id=case_id,
        submission_attempt_id=attempt_id,
        raw_status="Inspection Passed",
        received_at=dt.datetime(2026, 3, 16, 13, 0, 0, tzinfo=dt.UTC),
    )
    result3 = persist_external_status_event(request3)
    assert result3.normalized_status == ExternalStatusClass.INSPECTION_PASSED
