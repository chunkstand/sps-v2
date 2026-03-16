from __future__ import annotations

import asyncio
import logging

import ulid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sps.api.contracts.cases import (
    ComplianceEvaluationListResponse,
    ComplianceEvaluationResponse,
    IncentiveAssessmentListResponse,
    IncentiveAssessmentResponse,
    JurisdictionResolutionListResponse,
    JurisdictionResolutionResponse,
    RequirementSetListResponse,
    RequirementSetResponse,
)
from sps.api.contracts.intake import CreateCaseRequest, CreateCaseResponse, SiteAddress
from sps.config import get_settings
from sps.db.models import (
    ComplianceEvaluation,
    IncentiveAssessment,
    JurisdictionResolution,
    PermitCase,
    Project,
    RequirementSet,
)
from sps.db.session import get_db
from sps.workflows.permit_case.contracts import CaseState, PermitCaseWorkflowInput
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cases"])

_CASE_ID_PREFIX = "CASE-"
_PROJECT_ID_PREFIX = "PROJ-"


def _new_case_id() -> str:
    return f"{_CASE_ID_PREFIX}{ulid.new()}"


def _new_project_id() -> str:
    return f"{_PROJECT_ID_PREFIX}{ulid.new()}"


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
