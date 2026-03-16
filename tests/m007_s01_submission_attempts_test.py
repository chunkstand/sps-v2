from __future__ import annotations

import os

import pytest

from sps.db.models import EvidenceArtifact, PermitCase, SubmissionAttempt
from sps.db.session import get_sessionmaker
from sps.workflows.permit_case.activities import deterministic_submission_adapter, persist_submission_package
from sps.workflows.permit_case.contracts import (
    PersistSubmissionPackageRequest,
    SubmissionAdapterOutcome,
    SubmissionAdapterRequest,
    submission_attempt_idempotency_key,
)


@pytest.mark.integration
def test_submission_attempts_integration_flow() -> None:
    original_phase6 = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")
    original_phase7 = os.environ.get("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE")

    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"
        os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"

        case_id = "CASE-TEST-SUB-001"
        SessionLocal = get_sessionmaker()

        with SessionLocal() as session:
            with session.begin():
                existing_case = session.get(PermitCase, case_id)
                if not existing_case:
                    session.add(
                        PermitCase(
                            case_id=case_id,
                            tenant_id="tenant-test",
                            project_id=f"project-{case_id}",
                            case_state="DOCUMENT_COMPLETE",
                            review_state="PENDING",
                            submission_mode="AUTOMATED",
                            portal_support_level="FULLY_SUPPORTED",
                            current_package_id=None,
                            current_release_profile="default",
                            legal_hold=False,
                            closure_reason=None,
                        )
                    )

        package_id = persist_submission_package(
            PersistSubmissionPackageRequest(
                request_id="REQ-PKG-001",
                case_id=case_id,
            )
        )

        request = SubmissionAdapterRequest(
            request_id="REQ-SUB-001",
            submission_attempt_id="SUBATT-TEST-001",
            case_id=case_id,
            package_id=package_id,
            manifest_id="MANIFEST-001",
            target_portal_family="CITY_PORTAL_FAMILY_A",
            artifact_digests={},
            idempotency_key=submission_attempt_idempotency_key(case_id=case_id, attempt=1),
            attempt_number=1,
            correlation_id="corr-test-001",
        )

        result = deterministic_submission_adapter(request)
        assert result.outcome == SubmissionAdapterOutcome.SUCCESS
        assert result.receipt_artifact_id is not None
        assert result.external_tracking_id is not None

        with SessionLocal() as session:
            attempt = session.get(SubmissionAttempt, request.submission_attempt_id)
            assert attempt is not None
            assert attempt.status == "SUBMITTED"
            assert attempt.outcome == SubmissionAdapterOutcome.SUCCESS.value
            assert attempt.receipt_artifact_id == result.receipt_artifact_id
            assert attempt.external_tracking_id == result.external_tracking_id
            assert attempt.last_error is None

            receipt = session.get(EvidenceArtifact, result.receipt_artifact_id)
            assert receipt is not None
            assert receipt.artifact_class == "RECEIPT"
            assert receipt.linked_case_id == case_id

        result_again = deterministic_submission_adapter(request)
        assert result_again.receipt_artifact_id == result.receipt_artifact_id
        assert result_again.submission_attempt_id == result.submission_attempt_id
    finally:
        if original_phase6 is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original_phase6
        else:
            os.environ.pop("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE", None)

        if original_phase7 is not None:
            os.environ["SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE"] = original_phase7
        else:
            os.environ.pop("SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE", None)
