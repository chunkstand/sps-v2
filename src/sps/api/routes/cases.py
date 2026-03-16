from __future__ import annotations

import asyncio
import logging

import ulid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sps.api.contracts.intake import CreateCaseRequest, CreateCaseResponse, SiteAddress
from sps.config import get_settings
from sps.db.models import PermitCase, Project
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
