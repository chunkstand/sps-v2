from __future__ import annotations

from fastapi import APIRouter

from sps.api.contracts.cases import (
    ApprovalRecordListResponse,
    CorrectionTaskListResponse,
    ExternalStatusEventListResponse,
    ExternalStatusEventResponse,
    InspectionMilestoneListResponse,
    ManualFallbackPackageListResponse,
    ResubmissionPackageListResponse,
    SubmissionAttemptListResponse,
)
from sps.api.routes.cases_operations_impl import (
    get_case_approval_records,
    get_case_correction_tasks,
    get_case_external_status_events,
    get_case_inspection_milestones,
    get_case_manual_fallbacks,
    get_case_resubmission_packages,
    get_case_submission_attempts,
    ingest_external_status_event,
)

router = APIRouter()
router.add_api_route(
    "/cases/{case_id}/submission-attempts",
    get_case_submission_attempts,
    methods=["GET"],
    response_model=SubmissionAttemptListResponse,
)
router.add_api_route(
    "/cases/{case_id}/external-status-events",
    ingest_external_status_event,
    methods=["POST"],
    response_model=ExternalStatusEventResponse,
    status_code=201,
)
router.add_api_route(
    "/cases/{case_id}/external-status-events",
    get_case_external_status_events,
    methods=["GET"],
    response_model=ExternalStatusEventListResponse,
)
router.add_api_route(
    "/cases/{case_id}/manual-fallbacks",
    get_case_manual_fallbacks,
    methods=["GET"],
    response_model=ManualFallbackPackageListResponse,
)
router.add_api_route(
    "/cases/{case_id}/correction-tasks",
    get_case_correction_tasks,
    methods=["GET"],
    response_model=CorrectionTaskListResponse,
)
router.add_api_route(
    "/cases/{case_id}/resubmission-packages",
    get_case_resubmission_packages,
    methods=["GET"],
    response_model=ResubmissionPackageListResponse,
)
router.add_api_route(
    "/cases/{case_id}/approval-records",
    get_case_approval_records,
    methods=["GET"],
    response_model=ApprovalRecordListResponse,
)
router.add_api_route(
    "/cases/{case_id}/inspection-milestones",
    get_case_inspection_milestones,
    methods=["GET"],
    response_model=InspectionMilestoneListResponse,
)
