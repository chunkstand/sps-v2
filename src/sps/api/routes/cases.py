from __future__ import annotations

import asyncio
import datetime as dt
import logging

import ulid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sps.api.contracts.cases import (
    ApprovalRecordListResponse,
    ApprovalRecordResponse,
    ComplianceEvaluationListResponse,
    ComplianceEvaluationResponse,
    CorrectionTaskListResponse,
    CorrectionTaskResponse,
    DocumentReferenceResponse,
    EvidenceArtifactResponse,
    ExternalStatusEventIngestRequest,
    ExternalStatusEventListResponse,
    ExternalStatusEventResponse,
    IncentiveAssessmentListResponse,
    IncentiveAssessmentResponse,
    InspectionMilestoneListResponse,
    InspectionMilestoneResponse,
    JurisdictionResolutionListResponse,
    JurisdictionResolutionResponse,
    ManualFallbackPackageListResponse,
    ManualFallbackPackageResponse,
    RequirementSetListResponse,
    RequirementSetResponse,
    ResubmissionPackageListResponse,
    ResubmissionPackageResponse,
    SubmissionAttemptListResponse,
    SubmissionAttemptResponse,
    SubmissionManifestResponse,
    SubmissionPackageResponse,
)
from sps.api.contracts.intake import CreateCaseRequest, CreateCaseResponse, SiteAddress
from sps.auth.rbac import Role, require_roles
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
    PermitCase,
    Project,
    RequirementSet,
    ResubmissionPackage,
    SubmissionAttempt,
)
from sps.db.session import get_db
from sps.workflows.permit_case.activities import persist_external_status_event
from sps.workflows.permit_case.contracts import (
    CaseState,
    ExternalStatusNormalizationRequest,
    PermitCaseWorkflowInput,
    StatusEventSignal,
)
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cases"], dependencies=[Depends(require_roles(Role.INTAKE))])

_CASE_ID_PREFIX = "CASE-"
_PROJECT_ID_PREFIX = "PROJ-"
_EXTERNAL_STATUS_EVENT_PREFIX = "ESE-"


def _new_case_id() -> str:
    return f"{_CASE_ID_PREFIX}{ulid.new()}"


def _new_project_id() -> str:
    return f"{_PROJECT_ID_PREFIX}{ulid.new()}"


def _new_external_status_event_id() -> str:
    return f"{_EXTERNAL_STATUS_EVENT_PREFIX}{ulid.new()}"


def _format_address(site_address: SiteAddress) -> str:
    parts = [site_address.line1]
    if site_address.line2:
        parts.append(site_address.line2)
    parts.append(f"{site_address.city}, {site_address.state} {site_address.postal_code}")
    return ", ".join(parts)


def _jurisdiction_row_to_response(row: JurisdictionResolution) -> JurisdictionResolutionResponse:
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


def _requirement_row_to_response(row: RequirementSet) -> RequirementSetResponse:
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


def _compliance_row_to_response(row: ComplianceEvaluation) -> ComplianceEvaluationResponse:
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


def _incentive_row_to_response(row: IncentiveAssessment) -> IncentiveAssessmentResponse:
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


def _evidence_row_to_response(row: EvidenceArtifact) -> EvidenceArtifactResponse:
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


def _submission_attempt_row_to_response(
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
        receipt_evidence=_evidence_row_to_response(receipt) if receipt else None,
    )


def _external_status_row_to_response(row: ExternalStatusEvent) -> ExternalStatusEventResponse:
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


def _manual_fallback_row_to_response(
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
        proof_bundle_evidence=_evidence_row_to_response(proof_bundle) if proof_bundle else None,
    )


def _correction_task_row_to_response(row: CorrectionTask) -> CorrectionTaskResponse:
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


def _resubmission_package_row_to_response(row: ResubmissionPackage) -> ResubmissionPackageResponse:
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


def _approval_record_row_to_response(row: ApprovalRecord) -> ApprovalRecordResponse:
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


def _inspection_milestone_row_to_response(row: InspectionMilestone) -> InspectionMilestoneResponse:
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


async def _start_workflow(case_id: str) -> None:
    settings = get_settings()
    workflow_id = permit_case_workflow_id(case_id)

    try:
        client = await asyncio.wait_for(connect_client(), timeout=10.0)
        await asyncio.wait_for(
            client.start_workflow(
                PermitCaseWorkflow.run,
                PermitCaseWorkflowInput(case_id=case_id),
                id=workflow_id,
                task_queue=settings.temporal_task_queue,
            ),
            timeout=10.0,
        )
        logger.info(
            "intake_api.workflow_started case_id=%s workflow_id=%s",
            case_id,
            workflow_id,
        )
    except Exception as exc:  # pragma: no cover - best-effort start
        logger.warning(
            "intake_api.workflow_start_failed case_id=%s workflow_id=%s exc_type=%s",
            case_id,
            workflow_id,
            type(exc).__name__,
            exc_info=True,
        )


async def _send_status_event_signal(
    *,
    case_id: str,
    signal: StatusEventSignal,
) -> None:
    """Deliver StatusEvent signal to the waiting PermitCaseWorkflow.

    Failures are logged but must not bubble up to the caller — the Postgres
    write is the authoritative event; signal delivery is best-effort.
    """
    try:
        client = await asyncio.wait_for(connect_client(), timeout=10.0)
        workflow_id = permit_case_workflow_id(case_id)
        handle = client.get_workflow_handle(workflow_id)
        await asyncio.wait_for(
            handle.signal("StatusEvent", signal),
            timeout=10.0,
        )
        logger.info(
            "reviewer_api.signal_sent workflow_id=%s case_id=%s signal_type=StatusEvent event_id=%s",
            workflow_id,
            case_id,
            signal.event_id,
        )
    except Exception as exc:
        logger.warning(
            "reviewer_api.signal_failed workflow_id=%s case_id=%s signal_type=StatusEvent event_id=%s error=%s",
            permit_case_workflow_id(case_id),
            case_id,
            signal.event_id,
            type(exc).__name__,
            exc_info=True,
        )


@router.post("/cases", status_code=201)
async def create_case(req: CreateCaseRequest, db: Session = Depends(get_db)) -> CreateCaseResponse:
    case_id = _new_case_id()
    project_id = _new_project_id()

    permit_case = PermitCase(
        case_id=case_id,
        tenant_id=req.tenant_id,
        project_id=project_id,
        case_state=CaseState.INTAKE_PENDING.value,
        review_state="PENDING",
        submission_mode="AUTOMATED",
        portal_support_level="FULLY_SUPPORTED",
        current_package_id=None,
        current_release_profile="default",
        legal_hold=False,
        closure_reason=None,
    )

    project = Project(
        project_id=project_id,
        case_id=case_id,
        address=_format_address(req.site_address),
        parcel_id=req.parcel_id,
        project_type=req.project_type,
        system_size_kw=req.system_size_kw,
        battery_flag=req.battery_flag,
        service_upgrade_flag=req.service_upgrade_flag,
        trenching_flag=req.trenching_flag,
        structural_modification_flag=req.structural_modification_flag,
        roof_type=req.roof_type,
        occupancy_classification=req.occupancy_classification,
        utility_name=req.utility_name,
        contact_metadata={
            "requester": {"name": req.requester.name, "email": req.requester.email},
            "project_description": req.project_description,
            "intake_mode": req.intake_mode,
        },
    )

    try:
        with db.begin():
            db.add(permit_case)
            db.add(project)
    except SQLAlchemyError as exc:
        logger.exception(
            "intake_api.case_create_failed case_id=%s project_id=%s exc_type=%s",
            case_id,
            project_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "case_create_failed"},
        ) from exc

    logger.info(
        "intake_api.case_created case_id=%s project_id=%s",
        case_id,
        project_id,
    )

    await _start_workflow(case_id)

    return CreateCaseResponse(
        case_id=case_id,
        project_id=project_id,
        case_state=CaseState.INTAKE_PENDING,
    )


@router.get("/cases/{case_id}/jurisdiction", response_model=JurisdictionResolutionListResponse)
def get_case_jurisdiction(
    case_id: str,
    db: Session = Depends(get_db),
) -> JurisdictionResolutionListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.jurisdiction_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        rows = (
            db.query(JurisdictionResolution)
            .filter(JurisdictionResolution.case_id == case_id)
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.jurisdiction_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "jurisdiction_fetch_failed", "case_id": case_id},
        ) from exc

    if not rows:
        logger.warning("cases.jurisdiction_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "jurisdiction_not_ready",
                "case_id": case_id,
                "missing": "jurisdiction_resolution",
            },
        )

    logger.info("cases.jurisdiction_fetched case_id=%s count=%s", case_id, len(rows))
    return JurisdictionResolutionListResponse(
        case_id=case_id,
        jurisdictions=[_jurisdiction_row_to_response(row) for row in rows],
    )


@router.get("/cases/{case_id}/requirements", response_model=RequirementSetListResponse)
def get_case_requirements(
    case_id: str,
    db: Session = Depends(get_db),
) -> RequirementSetListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.requirements_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        rows = (
            db.query(RequirementSet)
            .filter(RequirementSet.case_id == case_id)
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.requirements_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "requirements_fetch_failed", "case_id": case_id},
        ) from exc

    if not rows:
        logger.warning("cases.requirements_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "requirements_not_ready",
                "case_id": case_id,
                "missing": "requirement_set",
            },
        )

    logger.info("cases.requirements_fetched case_id=%s count=%s", case_id, len(rows))
    return RequirementSetListResponse(
        case_id=case_id,
        requirement_sets=[_requirement_row_to_response(row) for row in rows],
    )


@router.get("/cases/{case_id}/compliance", response_model=ComplianceEvaluationListResponse)
def get_case_compliance(
    case_id: str,
    db: Session = Depends(get_db),
) -> ComplianceEvaluationListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.compliance_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        rows = (
            db.query(ComplianceEvaluation)
            .filter(ComplianceEvaluation.case_id == case_id)
            .order_by(ComplianceEvaluation.evaluated_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.compliance_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "compliance_fetch_failed", "case_id": case_id},
        ) from exc

    if not rows:
        logger.warning("cases.compliance_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "compliance_not_ready",
                "case_id": case_id,
                "missing": "compliance_evaluation",
            },
        )

    logger.info("cases.compliance_fetched case_id=%s count=%s", case_id, len(rows))
    return ComplianceEvaluationListResponse(
        case_id=case_id,
        compliance_evaluations=[_compliance_row_to_response(row) for row in rows],
    )


@router.get("/cases/{case_id}/incentives", response_model=IncentiveAssessmentListResponse)
def get_case_incentives(
    case_id: str,
    db: Session = Depends(get_db),
) -> IncentiveAssessmentListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.incentives_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        rows = (
            db.query(IncentiveAssessment)
            .filter(IncentiveAssessment.case_id == case_id)
            .order_by(IncentiveAssessment.assessed_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.incentives_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "incentives_fetch_failed", "case_id": case_id},
        ) from exc

    if not rows:
        logger.warning("cases.incentives_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "incentives_not_ready",
                "case_id": case_id,
                "missing": "incentive_assessment",
            },
        )

    logger.info("cases.incentives_fetched case_id=%s count=%s", case_id, len(rows))
    return IncentiveAssessmentListResponse(
        case_id=case_id,
        incentive_assessments=[_incentive_row_to_response(row) for row in rows],
    )


@router.get("/cases/{case_id}/package", response_model=SubmissionPackageResponse)
def get_case_package(
    case_id: str,
    db: Session = Depends(get_db),
) -> SubmissionPackageResponse:
    """Retrieve the current submission package for a case."""
    from sps.api.contracts.cases import SubmissionPackageResponse
    from sps.db.models import SubmissionPackage
    
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.package_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )
        
        if case.current_package_id is None:
            logger.warning("cases.package_not_ready case_id=%s", case_id)
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "package_not_ready",
                    "case_id": case_id,
                    "missing": "current_package_id",
                },
            )
        
        package = db.get(SubmissionPackage, case.current_package_id)
        if package is None:
            logger.error(
                "cases.package_missing case_id=%s package_id=%s",
                case_id,
                case.current_package_id,
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "package_reference_broken",
                    "case_id": case_id,
                    "package_id": case.current_package_id,
                },
            )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.package_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "package_fetch_failed", "case_id": case_id},
        ) from exc
    
    logger.info("cases.package_fetched case_id=%s package_id=%s", case_id, package.package_id)
    return SubmissionPackageResponse(
        package_id=package.package_id,
        case_id=package.case_id,
        package_version=package.package_version,
        manifest_artifact_id=package.manifest_artifact_id,
        manifest_sha256_digest=package.manifest_sha256_digest,
        provenance=package.provenance,
        created_at=package.created_at,
        updated_at=package.updated_at,
    )


@router.get("/cases/{case_id}/manifest", response_model=SubmissionManifestResponse)
def get_case_manifest(
    case_id: str,
    db: Session = Depends(get_db),
) -> SubmissionManifestResponse:
    """Retrieve the manifest for the current submission package."""
    from sps.api.contracts.cases import DocumentReferenceResponse, SubmissionManifestResponse
    from sps.db.models import DocumentArtifact, EvidenceArtifact, SubmissionPackage
    
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.manifest_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )
        
        if case.current_package_id is None:
            logger.warning("cases.manifest_not_ready case_id=%s", case_id)
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "manifest_not_ready",
                    "case_id": case_id,
                    "missing": "current_package_id",
                },
            )
        
        package = db.get(SubmissionPackage, case.current_package_id)
        if package is None:
            logger.error(
                "cases.manifest_package_missing case_id=%s package_id=%s",
                case_id,
                case.current_package_id,
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "package_reference_broken",
                    "case_id": case_id,
                    "package_id": case.current_package_id,
                },
            )
        
        manifest_artifact = db.get(EvidenceArtifact, package.manifest_artifact_id)
        if manifest_artifact is None:
            logger.error(
                "cases.manifest_artifact_missing case_id=%s artifact_id=%s",
                case_id,
                package.manifest_artifact_id,
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "manifest_artifact_missing",
                    "case_id": case_id,
                    "artifact_id": package.manifest_artifact_id,
                },
            )
        
        # Fetch document artifacts for this package
        doc_artifacts = (
            db.query(DocumentArtifact)
            .filter(DocumentArtifact.package_id == package.package_id)
            .all()
        )
        
        document_references = [
            DocumentReferenceResponse(
                document_id=doc.document_id,
                document_type=doc.document_type,
                artifact_id=doc.evidence_artifact_id,
                sha256_digest=doc.sha256_digest,
            )
            for doc in doc_artifacts
        ]
        
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.manifest_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "manifest_fetch_failed", "case_id": case_id},
        ) from exc
    
    logger.info(
        "cases.manifest_fetched case_id=%s package_id=%s doc_count=%d",
        case_id,
        package.package_id,
        len(document_references),
    )
    
    # Build synthetic manifest response from package + document artifacts
    # In production, you might deserialize the actual manifest JSON from S3
    return SubmissionManifestResponse(
        manifest_id=package.manifest_artifact_id,
        case_id=package.case_id,
        package_version=package.package_version,
        generated_at=package.created_at or dt.datetime.now(dt.UTC),
        document_references=document_references,
        required_attachments=[],
        target_portal_family="acela",
        provenance=package.provenance,
    )


@router.get(
    "/cases/{case_id}/submission-attempts",
    response_model=SubmissionAttemptListResponse,
)
def get_case_submission_attempts(
    case_id: str,
    db: Session = Depends(get_db),
) -> SubmissionAttemptListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.submission_attempts_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        attempts = (
            db.query(SubmissionAttempt)
            .filter(SubmissionAttempt.case_id == case_id)
            .order_by(SubmissionAttempt.created_at.desc())
            .all()
        )

        receipt_ids = [
            attempt.receipt_artifact_id
            for attempt in attempts
            if attempt.receipt_artifact_id
        ]
        receipt_map: dict[str, EvidenceArtifact] = {}
        if receipt_ids:
            receipts = (
                db.query(EvidenceArtifact)
                .filter(EvidenceArtifact.artifact_id.in_(receipt_ids))
                .all()
            )
            receipt_map = {receipt.artifact_id: receipt for receipt in receipts}
            missing = set(receipt_ids) - set(receipt_map)
            for missing_id in missing:
                logger.warning(
                    "cases.submission_attempts_receipt_missing case_id=%s receipt_id=%s",
                    case_id,
                    missing_id,
                )

    except SQLAlchemyError as exc:
        logger.exception(
            "cases.submission_attempts_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "submission_attempts_fetch_failed", "case_id": case_id},
        ) from exc

    logger.info(
        "cases.submission_attempts_fetched case_id=%s count=%s",
        case_id,
        len(attempts),
    )
    return SubmissionAttemptListResponse(
        case_id=case_id,
        submission_attempts=[
            _submission_attempt_row_to_response(
                attempt,
                receipt_map.get(attempt.receipt_artifact_id) if attempt.receipt_artifact_id else None,
            )
            for attempt in attempts
        ],
    )


@router.post(
    "/cases/{case_id}/external-status-events",
    response_model=ExternalStatusEventResponse,
    status_code=201,
)
async def ingest_external_status_event(
    case_id: str,
    req: ExternalStatusEventIngestRequest,
    db: Session = Depends(get_db),
) -> ExternalStatusEventResponse:
    event_id = req.event_id or _new_external_status_event_id()

    case = db.get(PermitCase, case_id)
    if case is None:
        logger.warning("cases.external_status_missing_case case_id=%s", case_id)
        raise HTTPException(
            status_code=404,
            detail={"error": "case_not_found", "case_id": case_id},
        )

    attempt = db.get(SubmissionAttempt, req.submission_attempt_id)
    if attempt is None:
        logger.warning(
            "cases.external_status_missing_attempt case_id=%s submission_attempt_id=%s",
            case_id,
            req.submission_attempt_id,
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "submission_attempt_not_found",
                "case_id": case_id,
                "submission_attempt_id": req.submission_attempt_id,
            },
        )
    if attempt.case_id != case_id:
        logger.warning(
            "cases.external_status_attempt_case_mismatch case_id=%s submission_attempt_id=%s",
            case_id,
            req.submission_attempt_id,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": "submission_attempt_case_mismatch",
                "case_id": case_id,
                "submission_attempt_id": req.submission_attempt_id,
            },
        )

    request = ExternalStatusNormalizationRequest(
        event_id=event_id,
        case_id=case_id,
        submission_attempt_id=req.submission_attempt_id,
        raw_status=req.raw_status,
        received_at=req.received_at,
        evidence_ids=req.evidence_ids,
    )

    try:
        result = persist_external_status_event(request)
    except ValueError as exc:
        if str(exc) == "UNKNOWN_RAW_STATUS":
            logger.warning(
                "cases.external_status_unknown case_id=%s raw_status=%s", case_id, req.raw_status
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "external_status_unknown",
                    "case_id": case_id,
                    "raw_status": req.raw_status,
                },
            ) from exc
        raise
    except LookupError as exc:
        logger.warning(
            "cases.external_status_reference_missing case_id=%s submission_attempt_id=%s",
            case_id,
            req.submission_attempt_id,
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "external_status_reference_missing",
                "case_id": case_id,
                "submission_attempt_id": req.submission_attempt_id,
            },
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.external_status_persist_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "external_status_persist_failed", "case_id": case_id},
        ) from exc

    logger.info(
        "cases.external_status_ingested case_id=%s event_id=%s normalized_status=%s",
        case_id,
        result.event_id,
        result.normalized_status,
    )

    # Signal delivery — best-effort, must not affect HTTP response
    signal_payload = StatusEventSignal(
        event_id=result.event_id,
        case_id=result.case_id,
        submission_attempt_id=result.submission_attempt_id,
        normalized_status=result.normalized_status,
    )
    await _send_status_event_signal(
        case_id=case_id,
        signal=signal_payload,
    )

    return ExternalStatusEventResponse(
        event_id=result.event_id,
        case_id=result.case_id,
        submission_attempt_id=result.submission_attempt_id,
        raw_status=result.raw_status,
        normalized_status=result.normalized_status,
        confidence=result.confidence,
        auto_advance_eligible=result.auto_advance_eligible,
        evidence_ids=result.evidence_ids,
        mapping_version=result.mapping_version,
        received_at=result.received_at,
        created_at=None,
        updated_at=None,
    )


@router.get(
    "/cases/{case_id}/external-status-events",
    response_model=ExternalStatusEventListResponse,
)
def get_case_external_status_events(
    case_id: str,
    db: Session = Depends(get_db),
) -> ExternalStatusEventListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.external_status_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        rows = (
            db.query(ExternalStatusEvent)
            .filter(ExternalStatusEvent.case_id == case_id)
            .order_by(ExternalStatusEvent.received_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.external_status_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "external_status_fetch_failed", "case_id": case_id},
        ) from exc

    if not rows:
        logger.warning("cases.external_status_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "external_status_events_not_ready",
                "case_id": case_id,
                "missing": "external_status_event",
            },
        )

    logger.info("cases.external_status_fetched case_id=%s count=%s", case_id, len(rows))
    return ExternalStatusEventListResponse(
        case_id=case_id,
        external_status_events=[_external_status_row_to_response(row) for row in rows],
    )


@router.get(
    "/cases/{case_id}/manual-fallbacks",
    response_model=ManualFallbackPackageListResponse,
)
def get_case_manual_fallbacks(
    case_id: str,
    db: Session = Depends(get_db),
) -> ManualFallbackPackageListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.manual_fallbacks_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        packages = (
            db.query(ManualFallbackPackage)
            .filter(ManualFallbackPackage.case_id == case_id)
            .order_by(ManualFallbackPackage.created_at.desc())
            .all()
        )

        proof_ids = [
            package.proof_bundle_artifact_id
            for package in packages
            if package.proof_bundle_artifact_id
        ]
        proof_map: dict[str, EvidenceArtifact] = {}
        if proof_ids:
            proofs = (
                db.query(EvidenceArtifact)
                .filter(EvidenceArtifact.artifact_id.in_(proof_ids))
                .all()
            )
            proof_map = {proof.artifact_id: proof for proof in proofs}
            missing = set(proof_ids) - set(proof_map)
            for missing_id in missing:
                logger.warning(
                    "cases.manual_fallbacks_proof_missing case_id=%s proof_id=%s",
                    case_id,
                    missing_id,
                )

    except SQLAlchemyError as exc:
        logger.exception(
            "cases.manual_fallbacks_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "manual_fallbacks_fetch_failed", "case_id": case_id},
        ) from exc

    logger.info(
        "cases.manual_fallbacks_fetched case_id=%s count=%s",
        case_id,
        len(packages),
    )
    return ManualFallbackPackageListResponse(
        case_id=case_id,
        manual_fallback_packages=[
            _manual_fallback_row_to_response(
                package,
                proof_map.get(package.proof_bundle_artifact_id)
                if package.proof_bundle_artifact_id
                else None,
            )
            for package in packages
        ],
    )


@router.get(
    "/cases/{case_id}/correction-tasks",
    response_model=CorrectionTaskListResponse,
)
def get_case_correction_tasks(
    case_id: str,
    db: Session = Depends(get_db),
) -> CorrectionTaskListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.correction_tasks_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        tasks = (
            db.query(CorrectionTask)
            .filter(CorrectionTask.case_id == case_id)
            .order_by(CorrectionTask.created_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.correction_tasks_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "correction_tasks_fetch_failed", "case_id": case_id},
        ) from exc

    if not tasks:
        logger.warning("cases.correction_tasks_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "correction_tasks_not_ready",
                "case_id": case_id,
                "missing": "correction_task",
            },
        )

    logger.info("cases.correction_tasks_fetched case_id=%s count=%s", case_id, len(tasks))
    return CorrectionTaskListResponse(
        case_id=case_id,
        correction_tasks=[_correction_task_row_to_response(task) for task in tasks],
    )


@router.get(
    "/cases/{case_id}/resubmission-packages",
    response_model=ResubmissionPackageListResponse,
)
def get_case_resubmission_packages(
    case_id: str,
    db: Session = Depends(get_db),
) -> ResubmissionPackageListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.resubmission_packages_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        packages = (
            db.query(ResubmissionPackage)
            .filter(ResubmissionPackage.case_id == case_id)
            .order_by(ResubmissionPackage.created_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.resubmission_packages_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "resubmission_packages_fetch_failed", "case_id": case_id},
        ) from exc

    if not packages:
        logger.warning("cases.resubmission_packages_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "resubmission_packages_not_ready",
                "case_id": case_id,
                "missing": "resubmission_package",
            },
        )

    logger.info(
        "cases.resubmission_packages_fetched case_id=%s count=%s",
        case_id,
        len(packages),
    )
    return ResubmissionPackageListResponse(
        case_id=case_id,
        resubmission_packages=[
            _resubmission_package_row_to_response(package) for package in packages
        ],
    )


@router.get(
    "/cases/{case_id}/approval-records",
    response_model=ApprovalRecordListResponse,
)
def get_case_approval_records(
    case_id: str,
    db: Session = Depends(get_db),
) -> ApprovalRecordListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.approval_records_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        records = (
            db.query(ApprovalRecord)
            .filter(ApprovalRecord.case_id == case_id)
            .order_by(ApprovalRecord.created_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.approval_records_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "approval_records_fetch_failed", "case_id": case_id},
        ) from exc

    if not records:
        logger.warning("cases.approval_records_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "approval_records_not_ready",
                "case_id": case_id,
                "missing": "approval_record",
            },
        )

    logger.info("cases.approval_records_fetched case_id=%s count=%s", case_id, len(records))
    return ApprovalRecordListResponse(
        case_id=case_id,
        approval_records=[_approval_record_row_to_response(record) for record in records],
    )


@router.get(
    "/cases/{case_id}/inspection-milestones",
    response_model=InspectionMilestoneListResponse,
)
def get_case_inspection_milestones(
    case_id: str,
    db: Session = Depends(get_db),
) -> InspectionMilestoneListResponse:
    try:
        case = db.get(PermitCase, case_id)
        if case is None:
            logger.warning("cases.inspection_milestones_missing_case case_id=%s", case_id)
            raise HTTPException(
                status_code=404,
                detail={"error": "case_not_found", "case_id": case_id},
            )

        milestones = (
            db.query(InspectionMilestone)
            .filter(InspectionMilestone.case_id == case_id)
            .order_by(InspectionMilestone.created_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "cases.inspection_milestones_fetch_failed case_id=%s exc_type=%s",
            case_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "inspection_milestones_fetch_failed", "case_id": case_id},
        ) from exc

    if not milestones:
        logger.warning("cases.inspection_milestones_missing case_id=%s", case_id)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "inspection_milestones_not_ready",
                "case_id": case_id,
                "missing": "inspection_milestone",
            },
        )

    logger.info(
        "cases.inspection_milestones_fetched case_id=%s count=%s",
        case_id,
        len(milestones),
    )
    return InspectionMilestoneListResponse(
        case_id=case_id,
        inspection_milestones=[
            _inspection_milestone_row_to_response(milestone) for milestone in milestones
        ],
    )

