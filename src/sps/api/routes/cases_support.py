from __future__ import annotations

import logging

import ulid

from sps.api.contracts.cases import (
    ApprovalRecordResponse,
    ComplianceEvaluationResponse,
    CorrectionTaskResponse,
    EvidenceArtifactResponse,
    ExternalStatusEventResponse,
    IncentiveAssessmentResponse,
    InspectionMilestoneResponse,
    JurisdictionResolutionResponse,
    ManualFallbackPackageResponse,
    RequirementSetResponse,
    ResubmissionPackageResponse,
    SubmissionAttemptResponse,
)
from sps.api.contracts.intake import SiteAddress
from sps.config import get_settings
from sps.db.models import (
    ApprovalRecord,
    ComplianceEvaluation,
    CorrectionTask,
    EvidenceArtifact,
    ExternalStatusEvent,
    IncentiveAssessment,
    InspectionMilestone,
    JurisdictionResolution,
    ManualFallbackPackage,
    RequirementSet,
    ResubmissionPackage,
    SubmissionAttempt,
)
from sps.documents.contracts import SubmissionManifestPayload
from sps.documents.registry import EvidenceRegistry
from sps.storage.s3 import S3Storage

logger = logging.getLogger("sps.api.routes.cases_impl")

_CASE_ID_PREFIX = "CASE-"
_PROJECT_ID_PREFIX = "PROJ-"
_EXTERNAL_STATUS_EVENT_PREFIX = "ESE-"
_DEFAULT_LIST_LIMIT = 20
_MAX_LIST_LIMIT = 100


def new_case_id() -> str:
    return f"{_CASE_ID_PREFIX}{ulid.new()}"


def new_project_id() -> str:
    return f"{_PROJECT_ID_PREFIX}{ulid.new()}"


def new_external_status_event_id() -> str:
    return f"{_EXTERNAL_STATUS_EVENT_PREFIX}{ulid.new()}"


def clamp_list_limit(limit: int) -> int:
    return min(limit, _MAX_LIST_LIMIT)


def evidence_registry() -> EvidenceRegistry:
    settings = get_settings()
    return EvidenceRegistry(storage=S3Storage(settings=settings), settings=settings)


def load_submission_manifest(manifest_artifact: EvidenceArtifact) -> SubmissionManifestPayload:
    registry = evidence_registry()
    content = registry.read_artifact_bytes(storage_uri=manifest_artifact.storage_uri)
    return SubmissionManifestPayload.model_validate_json(content)


def format_address(site_address: SiteAddress) -> str:
    parts = [site_address.line1]
    if site_address.line2:
        parts.append(site_address.line2)
    parts.append(f"{site_address.city}, {site_address.state} {site_address.postal_code}")
    return ", ".join(parts)


def jurisdiction_row_to_response(row: JurisdictionResolution) -> JurisdictionResolutionResponse:
    return JurisdictionResolutionResponse(
        jurisdiction_resolution_id=row.jurisdiction_resolution_id,
        case_id=row.case_id,
        city_authority_id=row.city_authority_id,
        county_authority_id=row.county_authority_id,
        state_authority_id=row.state_authority_id,
        utility_authority_id=row.utility_authority_id,
        zoning_district=row.zoning_district,
        overlays=row.overlays,
        permitting_portal_family=row.permitting_portal_family,
        support_level=row.support_level,
        manual_requirements=row.manual_requirements,
        evidence_ids=row.evidence_ids or [],
        provenance=row.provenance,
        evidence_payload=row.evidence_payload,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def requirement_row_to_response(row: RequirementSet) -> RequirementSetResponse:
    return RequirementSetResponse(
        requirement_set_id=row.requirement_set_id,
        case_id=row.case_id,
        jurisdiction_ids=row.jurisdiction_ids or [],
        permit_types=row.permit_types or [],
        forms_required=row.forms_required or [],
        attachments_required=row.attachments_required or [],
        fee_rules=row.fee_rules,
        source_rankings=row.source_rankings or [],
        freshness_state=row.freshness_state,
        freshness_expires_at=row.freshness_expires_at,
        contradiction_state=row.contradiction_state,
        evidence_ids=row.evidence_ids or [],
        provenance=row.provenance,
        evidence_payload=row.evidence_payload,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def compliance_row_to_response(row: ComplianceEvaluation) -> ComplianceEvaluationResponse:
    return ComplianceEvaluationResponse(
        compliance_evaluation_id=row.compliance_evaluation_id,
        case_id=row.case_id,
        schema_version=row.schema_version,
        evaluated_at=row.evaluated_at,
        rule_results=row.rule_results or [],
        blockers=row.blockers or [],
        warnings=row.warnings or [],
        provenance=row.provenance,
        evidence_payload=row.evidence_payload,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def incentive_row_to_response(row: IncentiveAssessment) -> IncentiveAssessmentResponse:
    return IncentiveAssessmentResponse(
        incentive_assessment_id=row.incentive_assessment_id,
        case_id=row.case_id,
        schema_version=row.schema_version,
        assessed_at=row.assessed_at,
        candidate_programs=row.candidate_programs or [],
        eligibility_status=row.eligibility_status,
        stacking_conflicts=row.stacking_conflicts or [],
        deadlines=row.deadlines,
        source_ids=row.source_ids or [],
        advisory_value_range=row.advisory_value_range,
        authoritative_value_state=row.authoritative_value_state,
        provenance=row.provenance,
        evidence_payload=row.evidence_payload,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def evidence_row_to_response(row: EvidenceArtifact) -> EvidenceArtifactResponse:
    return EvidenceArtifactResponse(
        artifact_id=row.artifact_id,
        artifact_class=row.artifact_class,
        producing_service=row.producing_service,
        linked_case_id=row.linked_case_id,
        linked_object_id=row.linked_object_id,
        authoritativeness=row.authoritativeness,
        retention_class=row.retention_class,
        checksum=row.checksum,
        storage_uri=row.storage_uri,
        content_bytes=row.content_bytes,
        content_type=row.content_type,
        provenance=row.provenance,
        created_at=row.created_at,
        expires_at=row.expires_at,
    )


def submission_attempt_row_to_response(
    row: SubmissionAttempt,
    receipt: EvidenceArtifact | None,
) -> SubmissionAttemptResponse:
    return SubmissionAttemptResponse(
        submission_attempt_id=row.submission_attempt_id,
        case_id=row.case_id,
        package_id=row.package_id,
        manifest_artifact_id=row.manifest_artifact_id,
        target_portal_family=row.target_portal_family,
        portal_support_level=row.portal_support_level,
        request_id=row.request_id,
        idempotency_key=row.idempotency_key,
        attempt_number=row.attempt_number,
        status=row.status,
        outcome=row.outcome,
        external_tracking_id=row.external_tracking_id,
        receipt_artifact_id=row.receipt_artifact_id,
        submitted_at=row.submitted_at,
        failure_class=row.failure_class,
        last_error=row.last_error,
        last_error_context=row.last_error_context,
        created_at=row.created_at,
        updated_at=row.updated_at,
        receipt_evidence=evidence_row_to_response(receipt) if receipt else None,
    )


def external_status_row_to_response(row: ExternalStatusEvent) -> ExternalStatusEventResponse:
    return ExternalStatusEventResponse(
        event_id=row.event_id,
        case_id=row.case_id,
        submission_attempt_id=row.submission_attempt_id,
        raw_status=row.raw_status,
        normalized_status=row.normalized_status,
        confidence=row.confidence,
        auto_advance_eligible=row.auto_advance_eligible,
        evidence_ids=row.evidence_ids or [],
        mapping_version=row.mapping_version,
        received_at=row.received_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def manual_fallback_row_to_response(
    row: ManualFallbackPackage,
    proof_bundle: EvidenceArtifact | None,
) -> ManualFallbackPackageResponse:
    return ManualFallbackPackageResponse(
        manual_fallback_package_id=row.manual_fallback_package_id,
        case_id=row.case_id,
        package_id=row.package_id,
        submission_attempt_id=row.submission_attempt_id,
        package_version=row.package_version,
        package_hash=row.package_hash,
        reason=row.reason,
        portal_support_level=row.portal_support_level,
        channel_type=row.channel_type,
        proof_bundle_state=row.proof_bundle_state,
        required_attachments=row.required_attachments or [],
        operator_instructions=row.operator_instructions or [],
        required_proof_types=row.required_proof_types or [],
        escalation_owner=row.escalation_owner,
        proof_bundle_artifact_id=row.proof_bundle_artifact_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        proof_bundle_evidence=evidence_row_to_response(proof_bundle) if proof_bundle else None,
    )


def correction_task_row_to_response(row: CorrectionTask) -> CorrectionTaskResponse:
    return CorrectionTaskResponse(
        correction_task_id=row.correction_task_id,
        case_id=row.case_id,
        submission_attempt_id=row.submission_attempt_id,
        status=row.status,
        summary=row.summary,
        requested_at=row.requested_at,
        due_at=row.due_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def resubmission_package_row_to_response(row: ResubmissionPackage) -> ResubmissionPackageResponse:
    return ResubmissionPackageResponse(
        resubmission_package_id=row.resubmission_package_id,
        case_id=row.case_id,
        submission_attempt_id=row.submission_attempt_id,
        package_id=row.package_id,
        package_version=row.package_version,
        status=row.status,
        submitted_at=row.submitted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def approval_record_row_to_response(row: ApprovalRecord) -> ApprovalRecordResponse:
    return ApprovalRecordResponse(
        approval_record_id=row.approval_record_id,
        case_id=row.case_id,
        submission_attempt_id=row.submission_attempt_id,
        decision=row.decision,
        authority=row.authority,
        decided_at=row.decided_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def inspection_milestone_row_to_response(row: InspectionMilestone) -> InspectionMilestoneResponse:
    return InspectionMilestoneResponse(
        inspection_milestone_id=row.inspection_milestone_id,
        case_id=row.case_id,
        submission_attempt_id=row.submission_attempt_id,
        milestone_type=row.milestone_type,
        status=row.status,
        scheduled_for=row.scheduled_for,
        completed_at=row.completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
