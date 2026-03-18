from __future__ import annotations

import asyncio

from fastapi import Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sps.api.contracts.cases import (
    ApprovalRecordListResponse,
    CorrectionTaskListResponse,
    ExternalStatusEventIngestRequest,
    ExternalStatusEventListResponse,
    ExternalStatusEventResponse,
    InspectionMilestoneListResponse,
    ManualFallbackPackageListResponse,
    ResubmissionPackageListResponse,
    SubmissionAttemptListResponse,
)
from sps.db.models import (
    ApprovalRecord,
    CorrectionTask,
    ExternalStatusEvent,
    InspectionMilestone,
    ManualFallbackPackage,
    SubmissionAttempt,
    ResubmissionPackage,
)
from sps.db.session import get_db
from sps.workflows.permit_case.activities import persist_external_status_event
from sps.workflows.permit_case.contracts import ExternalStatusNormalizationRequest, StatusEventSignal
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.temporal import connect_client

from .cases_queries import fetch_artifact_map, fetch_case_rows, get_case_or_404
from .cases_support import (
    approval_record_row_to_response,
    clamp_list_limit,
    correction_task_row_to_response,
    external_status_row_to_response,
    inspection_milestone_row_to_response,
    logger,
    manual_fallback_row_to_response,
    new_external_status_event_id,
    resubmission_package_row_to_response,
    submission_attempt_row_to_response,
)


async def _send_status_event_signal(*, case_id: str, signal: StatusEventSignal) -> None:
    try:
        client = await asyncio.wait_for(connect_client(), timeout=10.0)
        workflow_id = permit_case_workflow_id(case_id)
        handle = client.get_workflow_handle(workflow_id)
        await asyncio.wait_for(handle.signal("StatusEvent", signal), timeout=10.0)
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


def get_case_submission_attempts(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> SubmissionAttemptListResponse:
    attempts = fetch_case_rows(
        db,
        case_id=case_id,
        model=SubmissionAttempt,
        limit=clamp_list_limit(limit),
        order_by=(SubmissionAttempt.created_at.desc(), SubmissionAttempt.submission_attempt_id.desc()),
        missing_case_event="cases.submission_attempts_missing_case",
        failure_event="cases.submission_attempts_fetch_failed",
        failure_error="submission_attempts_fetch_failed",
    )
    receipt_map = fetch_artifact_map(
        db,
        [attempt.receipt_artifact_id for attempt in attempts if attempt.receipt_artifact_id],
        missing_event="cases.submission_attempts_receipt_missing",
        case_id=case_id,
    )
    logger.info("cases.submission_attempts_fetched case_id=%s count=%s", case_id, len(attempts))
    return SubmissionAttemptListResponse(
        case_id=case_id,
        submission_attempts=[
            submission_attempt_row_to_response(
                attempt,
                receipt_map.get(attempt.receipt_artifact_id) if attempt.receipt_artifact_id else None,
            )
            for attempt in attempts
        ],
    )


async def ingest_external_status_event(
    case_id: str,
    req: ExternalStatusEventIngestRequest,
    db: Session = Depends(get_db),
) -> ExternalStatusEventResponse:
    event_id = req.event_id or new_external_status_event_id()
    get_case_or_404(db, case_id, missing_case_event="cases.external_status_missing_case")

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
            logger.warning("cases.external_status_unknown case_id=%s raw_status=%s", case_id, req.raw_status)
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
        logger.exception("cases.external_status_persist_failed case_id=%s exc_type=%s", case_id, type(exc).__name__)
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
    await _send_status_event_signal(
        case_id=case_id,
        signal=StatusEventSignal(
            event_id=result.event_id,
            case_id=result.case_id,
            submission_attempt_id=result.submission_attempt_id,
            normalized_status=result.normalized_status,
        ),
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


def get_case_external_status_events(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> ExternalStatusEventListResponse:
    rows = fetch_case_rows(
        db,
        case_id=case_id,
        model=ExternalStatusEvent,
        limit=clamp_list_limit(limit),
        order_by=(ExternalStatusEvent.received_at.desc(), ExternalStatusEvent.event_id.desc()),
        missing_case_event="cases.external_status_missing_case",
        failure_event="cases.external_status_fetch_failed",
        failure_error="external_status_fetch_failed",
        missing_rows_event="cases.external_status_missing",
        not_ready_error="external_status_events_not_ready",
        missing_name="external_status_event",
    )
    logger.info("cases.external_status_fetched case_id=%s count=%s", case_id, len(rows))
    return ExternalStatusEventListResponse(
        case_id=case_id,
        external_status_events=[external_status_row_to_response(row) for row in rows],
    )


def get_case_manual_fallbacks(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> ManualFallbackPackageListResponse:
    packages = fetch_case_rows(
        db,
        case_id=case_id,
        model=ManualFallbackPackage,
        limit=clamp_list_limit(limit),
        order_by=(ManualFallbackPackage.created_at.desc(), ManualFallbackPackage.manual_fallback_package_id.desc()),
        missing_case_event="cases.manual_fallbacks_missing_case",
        failure_event="cases.manual_fallbacks_fetch_failed",
        failure_error="manual_fallbacks_fetch_failed",
    )
    proof_map = fetch_artifact_map(
        db,
        [package.proof_bundle_artifact_id for package in packages if package.proof_bundle_artifact_id],
        missing_event="cases.manual_fallbacks_proof_missing",
        case_id=case_id,
    )
    logger.info("cases.manual_fallbacks_fetched case_id=%s count=%s", case_id, len(packages))
    return ManualFallbackPackageListResponse(
        case_id=case_id,
        manual_fallback_packages=[
            manual_fallback_row_to_response(
                package,
                proof_map.get(package.proof_bundle_artifact_id) if package.proof_bundle_artifact_id else None,
            )
            for package in packages
        ],
    )


def get_case_correction_tasks(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> CorrectionTaskListResponse:
    tasks = fetch_case_rows(
        db,
        case_id=case_id,
        model=CorrectionTask,
        limit=clamp_list_limit(limit),
        order_by=(CorrectionTask.created_at.desc(), CorrectionTask.correction_task_id.desc()),
        missing_case_event="cases.correction_tasks_missing_case",
        failure_event="cases.correction_tasks_fetch_failed",
        failure_error="correction_tasks_fetch_failed",
        missing_rows_event="cases.correction_tasks_missing",
        not_ready_error="correction_tasks_not_ready",
        missing_name="correction_task",
    )
    logger.info("cases.correction_tasks_fetched case_id=%s count=%s", case_id, len(tasks))
    return CorrectionTaskListResponse(
        case_id=case_id,
        correction_tasks=[correction_task_row_to_response(task) for task in tasks],
    )


def get_case_resubmission_packages(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> ResubmissionPackageListResponse:
    packages = fetch_case_rows(
        db,
        case_id=case_id,
        model=ResubmissionPackage,
        limit=clamp_list_limit(limit),
        order_by=(ResubmissionPackage.created_at.desc(), ResubmissionPackage.resubmission_package_id.desc()),
        missing_case_event="cases.resubmission_packages_missing_case",
        failure_event="cases.resubmission_packages_fetch_failed",
        failure_error="resubmission_packages_fetch_failed",
        missing_rows_event="cases.resubmission_packages_missing",
        not_ready_error="resubmission_packages_not_ready",
        missing_name="resubmission_package",
    )
    logger.info("cases.resubmission_packages_fetched case_id=%s count=%s", case_id, len(packages))
    return ResubmissionPackageListResponse(
        case_id=case_id,
        resubmission_packages=[resubmission_package_row_to_response(package) for package in packages],
    )


def get_case_approval_records(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> ApprovalRecordListResponse:
    records = fetch_case_rows(
        db,
        case_id=case_id,
        model=ApprovalRecord,
        limit=clamp_list_limit(limit),
        order_by=(ApprovalRecord.created_at.desc(), ApprovalRecord.approval_record_id.desc()),
        missing_case_event="cases.approval_records_missing_case",
        failure_event="cases.approval_records_fetch_failed",
        failure_error="approval_records_fetch_failed",
        missing_rows_event="cases.approval_records_missing",
        not_ready_error="approval_records_not_ready",
        missing_name="approval_record",
    )
    logger.info("cases.approval_records_fetched case_id=%s count=%s", case_id, len(records))
    return ApprovalRecordListResponse(
        case_id=case_id,
        approval_records=[approval_record_row_to_response(record) for record in records],
    )


def get_case_inspection_milestones(
    case_id: str,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> InspectionMilestoneListResponse:
    milestones = fetch_case_rows(
        db,
        case_id=case_id,
        model=InspectionMilestone,
        limit=clamp_list_limit(limit),
        order_by=(InspectionMilestone.created_at.desc(), InspectionMilestone.inspection_milestone_id.desc()),
        missing_case_event="cases.inspection_milestones_missing_case",
        failure_event="cases.inspection_milestones_fetch_failed",
        failure_error="inspection_milestones_fetch_failed",
        missing_rows_event="cases.inspection_milestones_missing",
        not_ready_error="inspection_milestones_not_ready",
        missing_name="inspection_milestone",
    )
    logger.info("cases.inspection_milestones_fetched case_id=%s count=%s", case_id, len(milestones))
    return InspectionMilestoneListResponse(
        case_id=case_id,
        inspection_milestones=[inspection_milestone_row_to_response(milestone) for milestone in milestones],
    )
