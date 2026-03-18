from __future__ import annotations

from fastapi import APIRouter

from sps.api.contracts.cases import (
    ComplianceEvaluationListResponse,
    IncentiveAssessmentListResponse,
    JurisdictionResolutionListResponse,
    RequirementSetListResponse,
    SubmissionManifestResponse,
    SubmissionPackageResponse,
)
from sps.api.routes.cases_read_impl import (
    get_case_compliance,
    get_case_incentives,
    get_case_jurisdiction,
    get_case_manifest,
    get_case_package,
    get_case_requirements,
)

router = APIRouter()
router.add_api_route(
    "/cases/{case_id}/jurisdiction",
    get_case_jurisdiction,
    methods=["GET"],
    response_model=JurisdictionResolutionListResponse,
)
router.add_api_route(
    "/cases/{case_id}/requirements",
    get_case_requirements,
    methods=["GET"],
    response_model=RequirementSetListResponse,
)
router.add_api_route(
    "/cases/{case_id}/compliance",
    get_case_compliance,
    methods=["GET"],
    response_model=ComplianceEvaluationListResponse,
)
router.add_api_route(
    "/cases/{case_id}/incentives",
    get_case_incentives,
    methods=["GET"],
    response_model=IncentiveAssessmentListResponse,
)
router.add_api_route(
    "/cases/{case_id}/package",
    get_case_package,
    methods=["GET"],
    response_model=SubmissionPackageResponse,
)
router.add_api_route(
    "/cases/{case_id}/manifest",
    get_case_manifest,
    methods=["GET"],
    response_model=SubmissionManifestResponse,
)
