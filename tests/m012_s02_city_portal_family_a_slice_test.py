from __future__ import annotations

import datetime as dt
import time

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sps.db.models import (
    ApprovalRecord,
    ComplianceEvaluation,
    ExternalStatusEvent,
    JurisdictionResolution,
    ManualFallbackPackage,
    PermitCase,
    RequirementSet,
    ResubmissionPackage,
    ReviewDecision,
    SubmissionAttempt,
    SubmissionPackage,
)
from sps.db.session import get_engine, get_sessionmaker
from sps.workflows.permit_case.activities import (
    deterministic_submission_adapter,
    persist_approval_record,
    persist_compliance_evaluation,
    persist_external_status_event,
    persist_jurisdiction_resolutions,
    persist_requirement_sets,
    persist_resubmission_package,
    persist_review_decision,
    persist_submission_package,
)
from sps.workflows.permit_case.contracts import (
    ExternalStatusClass,
    ExternalStatusNormalizationRequest,
    PersistApprovalRecordRequest,
    PersistComplianceEvaluationRequest,
    PersistJurisdictionResolutionRequest,
    PersistRequirementSetRequest,
    PersistResubmissionPackageRequest,
    PersistReviewDecisionRequest,
    PersistSubmissionPackageRequest,
    ReviewDecisionOutcome,
    ReviewerIndependenceStatus,
    SubmissionAdapterOutcome,
    SubmissionAdapterRequest,
    submission_attempt_idempotency_key,
)

pytestmark = pytest.mark.integration


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
                "TRUNCATE TABLE approval_records, resubmission_packages, review_decisions, "
                "external_status_events, manual_fallback_packages, submission_attempts, "
                "submission_packages, document_artifacts, evidence_artifacts, "
                "compliance_evaluations, requirement_sets, jurisdiction_resolutions, "
                "permit_cases CASCADE"
            )
        )


def test_city_portal_family_a_manual_slice_end_to_end() -> None:
    _wait_for_postgres_ready()
    _migrate_db()
    _reset_db()

    case_id = "CASE-CITYA-MANUAL-001"
    SessionLocal = get_sessionmaker()

    with SessionLocal() as session:
        with session.begin():
            existing_case = session.get(PermitCase, case_id)
            if existing_case is None:
                session.add(
                    PermitCase(
                        case_id=case_id,
                        tenant_id="tenant-citya",
                        project_id=f"project-{case_id}",
                        case_state="REVIEW_PENDING",
                        review_state="PENDING",
                        submission_mode="AUTOMATED",
                        portal_support_level="UNSUPPORTED",
                        current_package_id=None,
                        current_release_profile="default",
                        legal_hold=False,
                        closure_reason=None,
                    )
                )

    jurisdiction_ids = persist_jurisdiction_resolutions(
        PersistJurisdictionResolutionRequest(
            request_id="REQ-CITYA-JURISDICTION",
            case_id=case_id,
        )
    )
    requirement_ids = persist_requirement_sets(
        PersistRequirementSetRequest(
            request_id="REQ-CITYA-REQUIREMENTS",
            case_id=case_id,
        )
    )
    compliance_ids = persist_compliance_evaluation(
        PersistComplianceEvaluationRequest(
            request_id="REQ-CITYA-COMPLIANCE",
            case_id=case_id,
        )
    )
    package_id = persist_submission_package(
        PersistSubmissionPackageRequest(
            request_id="REQ-CITYA-PACKAGE",
            case_id=case_id,
        )
    )
    review_decision_id = persist_review_decision(
        PersistReviewDecisionRequest(
            decision_id="REV-CITYA-001",
            case_id=case_id,
            object_id=case_id,
            decision_outcome=ReviewDecisionOutcome.ACCEPT,
            reviewer_id="reviewer-citya",
            reviewer_independence_status=ReviewerIndependenceStatus.PASS,
            dissent_flag=False,
            decision_at=dt.datetime(2026, 3, 17, 9, 0, tzinfo=dt.UTC),
            idempotency_key="review/citya/001",
        )
    )

    submission_attempt_id = "SUBATT-CITYA-001"
    submission_result = deterministic_submission_adapter(
        SubmissionAdapterRequest(
            request_id="REQ-CITYA-SUBMIT",
            submission_attempt_id=submission_attempt_id,
            case_id=case_id,
            package_id=package_id,
            manifest_id="MANIFEST-CITYA-001",
            target_portal_family="CITY_PORTAL_FAMILY_A",
            artifact_digests={},
            idempotency_key=submission_attempt_idempotency_key(case_id=case_id, attempt=1),
            attempt_number=1,
            correlation_id="corr-citya-001",
        )
    )
    assert submission_result.outcome == SubmissionAdapterOutcome.UNSUPPORTED_WORKFLOW
    assert submission_result.manual_fallback_package_id is not None

    resubmission_status = persist_external_status_event(
        ExternalStatusNormalizationRequest(
            event_id="ESE-CITYA-RESUBMIT",
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            raw_status="Resubmission Required",
            received_at=dt.datetime(2026, 3, 17, 10, 0, tzinfo=dt.UTC),
        )
    )
    assert resubmission_status.normalized_status == ExternalStatusClass.RESUBMISSION_REQUESTED

    resubmission_package_id = persist_resubmission_package(
        PersistResubmissionPackageRequest(
            resubmission_package_id="RESPKG-CITYA-001",
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            package_id=package_id,
            package_version="1.0.0-citya",
            status="READY",
            submitted_at=dt.datetime(2026, 3, 17, 10, 30, tzinfo=dt.UTC),
        )
    )

    approval_status = persist_external_status_event(
        ExternalStatusNormalizationRequest(
            event_id="ESE-CITYA-APPROVAL",
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            raw_status="Final Approval",
            received_at=dt.datetime(2026, 3, 17, 11, 0, tzinfo=dt.UTC),
        )
    )
    assert approval_status.normalized_status == ExternalStatusClass.APPROVAL_FINAL

    approval_record_id = persist_approval_record(
        PersistApprovalRecordRequest(
            approval_record_id="APR-CITYA-001",
            case_id=case_id,
            submission_attempt_id=submission_attempt_id,
            decision="APPROVED",
            authority="CITY_PORTAL_FAMILY_A",
            decided_at=dt.datetime(2026, 3, 17, 11, 5, tzinfo=dt.UTC),
        )
    )

    with SessionLocal() as session:
        assert session.get(JurisdictionResolution, jurisdiction_ids[0]) is not None
        assert session.get(RequirementSet, requirement_ids[0]) is not None

        compliance = session.get(ComplianceEvaluation, compliance_ids[0])
        assert compliance is not None
        assert compliance.blockers == []

        package = session.get(SubmissionPackage, package_id)
        assert package is not None
        assert package.case_id == case_id

        review = session.get(ReviewDecision, review_decision_id)
        assert review is not None
        assert review.decision_outcome == ReviewDecisionOutcome.ACCEPT.value

        attempt = session.get(SubmissionAttempt, submission_attempt_id)
        assert attempt is not None
        assert attempt.outcome == SubmissionAdapterOutcome.UNSUPPORTED_WORKFLOW.value

        fallback = session.get(ManualFallbackPackage, submission_result.manual_fallback_package_id)
        assert fallback is not None
        assert fallback.channel_type == "official_authority_email"
        assert fallback.required_proof_types

        resubmission_event = session.get(ExternalStatusEvent, "ESE-CITYA-RESUBMIT")
        assert resubmission_event is not None
        assert resubmission_event.normalized_status == ExternalStatusClass.RESUBMISSION_REQUESTED.value
        assert resubmission_event.mapping_version == "2026-03-17.1"

        approval_event = session.get(ExternalStatusEvent, "ESE-CITYA-APPROVAL")
        assert approval_event is not None
        assert approval_event.normalized_status == ExternalStatusClass.APPROVAL_FINAL.value
        assert approval_event.mapping_version == "2026-03-17.1"

        resubmission = session.get(ResubmissionPackage, resubmission_package_id)
        assert resubmission is not None
        assert resubmission.package_id == package_id

        approval = session.get(ApprovalRecord, approval_record_id)
        assert approval is not None
        assert approval.authority == "CITY_PORTAL_FAMILY_A"
