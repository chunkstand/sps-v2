from __future__ import annotations
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sps.api.contracts.cases import (
    ComplianceEvaluationListResponse,
    DocumentReferenceResponse,
    IncentiveAssessmentListResponse,
    JurisdictionResolutionListResponse,
    RequirementSetListResponse,
    SubmissionManifestResponse,
    SubmissionPackageResponse,
)
from sps.db.models import ComplianceEvaluation, IncentiveAssessment, JurisdictionResolution, RequirementSet
from sps.db.session import get_db
from sps.storage.s3 import StorageError

from .cases_queries import fetch_case_rows, get_current_submission_package, get_manifest_artifact_for_case
from .cases_support import (
    clamp_list_limit,
    compliance_row_to_response,
    incentive_row_to_response,
    jurisdiction_row_to_response,
    load_submission_manifest,
    logger,
    requirement_row_to_response,
)


def get_case_jurisdiction(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> JurisdictionResolutionListResponse:
    rows = fetch_case_rows(
        db,
        case_id=case_id,
        model=JurisdictionResolution,
        limit=clamp_list_limit(limit),
        order_by=(JurisdictionResolution.created_at.desc(), JurisdictionResolution.jurisdiction_resolution_id.desc()),
        missing_case_event="cases.jurisdiction_missing_case",
        failure_event="cases.jurisdiction_fetch_failed",
        failure_error="jurisdiction_fetch_failed",
        missing_rows_event="cases.jurisdiction_missing",
        not_ready_error="jurisdiction_not_ready",
        missing_name="jurisdiction_resolution",
    )
    logger.info("cases.jurisdiction_fetched case_id=%s count=%s", case_id, len(rows))
    return JurisdictionResolutionListResponse(
        case_id=case_id,
        jurisdictions=[jurisdiction_row_to_response(row) for row in rows],
    )


def get_case_requirements(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> RequirementSetListResponse:
    rows = fetch_case_rows(
        db,
        case_id=case_id,
        model=RequirementSet,
        limit=clamp_list_limit(limit),
        order_by=(RequirementSet.created_at.desc(), RequirementSet.requirement_set_id.desc()),
        missing_case_event="cases.requirements_missing_case",
        failure_event="cases.requirements_fetch_failed",
        failure_error="requirements_fetch_failed",
        missing_rows_event="cases.requirements_missing",
        not_ready_error="requirements_not_ready",
        missing_name="requirement_set",
    )
    logger.info("cases.requirements_fetched case_id=%s count=%s", case_id, len(rows))
    return RequirementSetListResponse(
        case_id=case_id,
        requirement_sets=[requirement_row_to_response(row) for row in rows],
    )


def get_case_compliance(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> ComplianceEvaluationListResponse:
    rows = fetch_case_rows(
        db,
        case_id=case_id,
        model=ComplianceEvaluation,
        limit=clamp_list_limit(limit),
        order_by=(ComplianceEvaluation.evaluated_at.desc(), ComplianceEvaluation.compliance_evaluation_id.desc()),
        missing_case_event="cases.compliance_missing_case",
        failure_event="cases.compliance_fetch_failed",
        failure_error="compliance_fetch_failed",
        missing_rows_event="cases.compliance_missing",
        not_ready_error="compliance_not_ready",
        missing_name="compliance_evaluation",
    )
    logger.info("cases.compliance_fetched case_id=%s count=%s", case_id, len(rows))
    return ComplianceEvaluationListResponse(
        case_id=case_id,
        compliance_evaluations=[compliance_row_to_response(row) for row in rows],
    )


def get_case_incentives(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> IncentiveAssessmentListResponse:
    rows = fetch_case_rows(
        db,
        case_id=case_id,
        model=IncentiveAssessment,
        limit=clamp_list_limit(limit),
        order_by=(IncentiveAssessment.assessed_at.desc(), IncentiveAssessment.incentive_assessment_id.desc()),
        missing_case_event="cases.incentives_missing_case",
        failure_event="cases.incentives_fetch_failed",
        failure_error="incentives_fetch_failed",
        missing_rows_event="cases.incentives_missing",
        not_ready_error="incentives_not_ready",
        missing_name="incentive_assessment",
    )
    logger.info("cases.incentives_fetched case_id=%s count=%s", case_id, len(rows))
    return IncentiveAssessmentListResponse(
        case_id=case_id,
        incentive_assessments=[incentive_row_to_response(row) for row in rows],
    )


def get_case_package(case_id: str, db: Session = Depends(get_db)) -> SubmissionPackageResponse:
    package = get_current_submission_package(db, case_id)
    logger.info("cases.package_fetched case_id=%s package_id=%s", case_id, package.package_id)
    return SubmissionPackageResponse(
        package_id=package.package_id,
        case_id=package.case_id,
        package_version=package.package_version,
        manifest_artifact_id=package.manifest_artifact_id,
        manifest_sha256_digest=package.manifest_sha256_digest,
        provenance=package.provenance,
        created_at=package.created_at,
        updated_at=None,
    )


def get_case_manifest(case_id: str, db: Session = Depends(get_db)) -> SubmissionManifestResponse:
    package, manifest_artifact = get_manifest_artifact_for_case(db, case_id)
    try:
        manifest = load_submission_manifest(manifest_artifact)
    except (StorageError, ValueError) as exc:
        logger.exception(
            "cases.manifest_read_failed case_id=%s artifact_id=%s exc_type=%s",
            case_id,
            package.manifest_artifact_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "manifest_read_failed",
                "case_id": case_id,
                "artifact_id": package.manifest_artifact_id,
            },
        ) from exc

    logger.info(
        "cases.manifest_fetched case_id=%s package_id=%s doc_count=%d",
        case_id,
        package.package_id,
        len(manifest.document_references),
    )
    return SubmissionManifestResponse(
        manifest_id=manifest.manifest_id,
        case_id=manifest.case_id,
        package_version=manifest.package_version,
        generated_at=manifest.generated_at,
        document_references=[
            DocumentReferenceResponse(
                document_id=reference.document_id,
                document_type=reference.document_type.value,
                artifact_id=reference.artifact_id,
                sha256_digest=reference.sha256_digest,
            )
            for reference in manifest.document_references
        ],
        required_attachments=manifest.required_attachments,
        target_portal_family=manifest.target_portal_family,
        provenance=manifest.provenance,
    )
