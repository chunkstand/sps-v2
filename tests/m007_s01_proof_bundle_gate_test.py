from __future__ import annotations

import datetime as dt
import os

import pytest

from sps.db.models import EvidenceArtifact, ManualFallbackPackage, PermitCase, SubmissionPackage
from sps.db.session import get_sessionmaker
from sps.workflows.permit_case.activities import apply_state_transition, persist_submission_package
from sps.workflows.permit_case.contracts import ActorType, CaseState, PersistSubmissionPackageRequest, StateTransitionRequest


@pytest.mark.integration
def test_proof_bundle_gate_integration_flow() -> None:
    original_phase6 = os.environ.get("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE")

    try:
        os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = "CASE-EXAMPLE-001"

        case_id = "CASE-TEST-PROOF-001"
        manual_fallback_id = "MFP-PROOF-001"
        proof_artifact_id = "ART-PROOF-001"
        SessionLocal = get_sessionmaker()

        with SessionLocal() as session:
            with session.begin():
                session.query(ManualFallbackPackage).filter(
                    ManualFallbackPackage.manual_fallback_package_id == manual_fallback_id
                ).delete(synchronize_session=False)
                session.query(EvidenceArtifact).filter(
                    EvidenceArtifact.artifact_id == proof_artifact_id
                ).delete(synchronize_session=False)

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
                            portal_support_level="UNSUPPORTED",
                            current_package_id=None,
                            current_release_profile="default",
                            legal_hold=False,
                            closure_reason=None,
                        )
                    )

        package_id = persist_submission_package(
            PersistSubmissionPackageRequest(
                request_id="REQ-PKG-PROOF",
                case_id=case_id,
            )
        )

        with SessionLocal() as session:
            package = session.get(SubmissionPackage, package_id)
            assert package is not None
            session.add(
                ManualFallbackPackage(
                    manual_fallback_package_id=manual_fallback_id,
                    case_id=case_id,
                    package_id=package_id,
                    submission_attempt_id=None,
                    package_version=package.package_version,
                    package_hash=package.manifest_sha256_digest,
                    reason="UNSUPPORTED_PORTAL_WORKFLOW",
                    portal_support_level="UNSUPPORTED",
                    channel_type="official_authority_email",
                    proof_bundle_state="PENDING_REVIEW",
                    required_attachments=[package.manifest_artifact_id],
                    operator_instructions=["Submit via email"],
                    required_proof_types=["email_receipt"],
                    escalation_owner=None,
                    proof_bundle_artifact_id=None,
                )
            )
            session.commit()

        denied = apply_state_transition(
            StateTransitionRequest(
                request_id="REQ-TRANS-PROOF-001",
                case_id=case_id,
                from_state=CaseState.DOCUMENT_COMPLETE,
                to_state=CaseState.SUBMITTED,
                actor_type=ActorType.system_guard,
                actor_id="system-guard",
                correlation_id="corr-proof-001",
                causation_id=None,
                required_review_id=None,
                required_evidence_ids=[],
                override_id=None,
                requested_at=dt.datetime.now(dt.UTC),
                notes=None,
            )
        )
        assert denied.result == "denied"
        assert denied.event_type == "PROOF_BUNDLE_REQUIRED_DENIED"

        with SessionLocal() as session:
            session.add(
                EvidenceArtifact(
                    artifact_id=proof_artifact_id,
                    artifact_class="RECEIPT",
                    producing_service="manual-ops",
                    linked_case_id=case_id,
                    linked_object_id=manual_fallback_id,
                    authoritativeness="AUTHORITATIVE",
                    retention_class="CASE_CORE_7Y",
                    checksum="sha256:proof",
                    storage_uri=f"s3://evidence/{proof_artifact_id}.txt",
                    content_bytes=12,
                    content_type="text/plain",
                    provenance={"source": "manual-proof"},
                    created_at=dt.datetime.now(dt.UTC),
                    legal_hold_flag=False,
                )
            )
            fallback = session.get(ManualFallbackPackage, manual_fallback_id)
            assert fallback is not None
            fallback.proof_bundle_state = "CONFIRMED"
            fallback.proof_bundle_artifact_id = proof_artifact_id
            session.commit()

        applied = apply_state_transition(
            StateTransitionRequest(
                request_id="REQ-TRANS-PROOF-002",
                case_id=case_id,
                from_state=CaseState.DOCUMENT_COMPLETE,
                to_state=CaseState.SUBMITTED,
                actor_type=ActorType.system_guard,
                actor_id="system-guard",
                correlation_id="corr-proof-002",
                causation_id=None,
                required_review_id=None,
                required_evidence_ids=[],
                override_id=None,
                requested_at=dt.datetime.now(dt.UTC),
                notes=None,
            )
        )
        assert applied.result == "applied"

        with SessionLocal() as session:
            case = session.get(PermitCase, case_id)
            assert case is not None
            assert case.case_state == CaseState.SUBMITTED.value
    finally:
        if original_phase6 is not None:
            os.environ["SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"] = original_phase6
        else:
            os.environ.pop("SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE", None)
