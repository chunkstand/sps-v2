from __future__ import annotations

import datetime as dt

from sqlalchemy.exc import IntegrityError
from temporalio import activity

from sps.db.models import ApprovalRecord, CorrectionTask, InspectionMilestone, PermitCase, ResubmissionPackage, SubmissionAttempt
from sps.db.session import get_sessionmaker
from sps.workflows.permit_case.activities_shared import logger, safe_temporal_ids
from sps.workflows.permit_case.contracts import (
    PersistApprovalRecordRequest,
    PersistCorrectionTaskRequest,
    PersistInspectionMilestoneRequest,
    PersistResubmissionPackageRequest,
)


@activity.defn
def persist_correction_task(request: PersistCorrectionTaskRequest | dict) -> str:
    req = PersistCorrectionTaskRequest.model_validate(request)
    workflow_id, run_id = safe_temporal_ids()
    logger.info(
        "activity.start name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.correction_task_id,
    )

    requested_at = req.requested_at
    if requested_at and requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=dt.UTC)
    due_at = req.due_at
    if due_at and due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(CorrectionTask, req.correction_task_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.correction_task_id,
                        )
                        return req.correction_task_id

                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")
                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(f"submission_attempt not found for submission_attempt_id={req.submission_attempt_id}")
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            f"submission_attempt_case_mismatch attempt_id={req.submission_attempt_id} case_id={req.case_id}"
                        )

                    session.add(
                        CorrectionTask(
                            correction_task_id=req.correction_task_id,
                            case_id=req.case_id,
                            submission_attempt_id=req.submission_attempt_id,
                            status=req.status,
                            summary=req.summary,
                            requested_at=requested_at,
                            due_at=due_at,
                        )
                    )
                logger.info(
                    "activity.ok name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.correction_task_id,
                )
                return req.correction_task_id
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(CorrectionTask, req.correction_task_id)
            if existing is None:
                raise RuntimeError(
                    f"correction_tasks insert raced but row not found for correction_task_id={req.correction_task_id}"
                )
            logger.info(
                "activity.ok name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.correction_task_id,
            )
            return req.correction_task_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_correction_task workflow_id=%s run_id=%s case_id=%s correction_task_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.correction_task_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_resubmission_package(request: PersistResubmissionPackageRequest | dict) -> str:
    req = PersistResubmissionPackageRequest.model_validate(request)
    workflow_id, run_id = safe_temporal_ids()
    logger.info(
        "activity.start name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.resubmission_package_id,
    )

    submitted_at = req.submitted_at
    if submitted_at and submitted_at.tzinfo is None:
        submitted_at = submitted_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(ResubmissionPackage, req.resubmission_package_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.resubmission_package_id,
                        )
                        return req.resubmission_package_id

                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")
                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(f"submission_attempt not found for submission_attempt_id={req.submission_attempt_id}")
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            f"submission_attempt_case_mismatch attempt_id={req.submission_attempt_id} case_id={req.case_id}"
                        )

                    session.add(
                        ResubmissionPackage(
                            resubmission_package_id=req.resubmission_package_id,
                            case_id=req.case_id,
                            submission_attempt_id=req.submission_attempt_id,
                            package_id=req.package_id,
                            package_version=req.package_version,
                            status=req.status,
                            submitted_at=submitted_at,
                        )
                    )
                logger.info(
                    "activity.ok name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.resubmission_package_id,
                )
                return req.resubmission_package_id
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(ResubmissionPackage, req.resubmission_package_id)
            if existing is None:
                raise RuntimeError(
                    f"resubmission_packages insert raced but row not found for resubmission_package_id={req.resubmission_package_id}"
                )
            logger.info(
                "activity.ok name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.resubmission_package_id,
            )
            return req.resubmission_package_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_resubmission_package workflow_id=%s run_id=%s case_id=%s resubmission_package_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.resubmission_package_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_approval_record(request: PersistApprovalRecordRequest | dict) -> str:
    req = PersistApprovalRecordRequest.model_validate(request)
    workflow_id, run_id = safe_temporal_ids()
    logger.info(
        "activity.start name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.approval_record_id,
    )

    decided_at = req.decided_at
    if decided_at and decided_at.tzinfo is None:
        decided_at = decided_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(ApprovalRecord, req.approval_record_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.approval_record_id,
                        )
                        return req.approval_record_id

                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")
                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(f"submission_attempt not found for submission_attempt_id={req.submission_attempt_id}")
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            f"submission_attempt_case_mismatch attempt_id={req.submission_attempt_id} case_id={req.case_id}"
                        )

                    session.add(
                        ApprovalRecord(
                            approval_record_id=req.approval_record_id,
                            case_id=req.case_id,
                            submission_attempt_id=req.submission_attempt_id,
                            decision=req.decision,
                            authority=req.authority,
                            decided_at=decided_at,
                        )
                    )
                logger.info(
                    "activity.ok name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.approval_record_id,
                )
                return req.approval_record_id
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(ApprovalRecord, req.approval_record_id)
            if existing is None:
                raise RuntimeError(
                    f"approval_records insert raced but row not found for approval_record_id={req.approval_record_id}"
                )
            logger.info(
                "activity.ok name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.approval_record_id,
            )
            return req.approval_record_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_approval_record workflow_id=%s run_id=%s case_id=%s approval_record_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.approval_record_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_inspection_milestone(request: PersistInspectionMilestoneRequest | dict) -> str:
    req = PersistInspectionMilestoneRequest.model_validate(request)
    workflow_id, run_id = safe_temporal_ids()
    logger.info(
        "activity.start name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.inspection_milestone_id,
    )

    scheduled_for = req.scheduled_for
    if scheduled_for and scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=dt.UTC)
    completed_at = req.completed_at
    if completed_at and completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=dt.UTC)

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.get(InspectionMilestone, req.inspection_milestone_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            req.inspection_milestone_id,
                        )
                        return req.inspection_milestone_id

                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise LookupError(f"permit_case not found for case_id={req.case_id}")
                    attempt = session.get(SubmissionAttempt, req.submission_attempt_id)
                    if attempt is None:
                        raise LookupError(f"submission_attempt not found for submission_attempt_id={req.submission_attempt_id}")
                    if attempt.case_id != req.case_id:
                        raise LookupError(
                            f"submission_attempt_case_mismatch attempt_id={req.submission_attempt_id} case_id={req.case_id}"
                        )

                    session.add(
                        InspectionMilestone(
                            inspection_milestone_id=req.inspection_milestone_id,
                            case_id=req.case_id,
                            submission_attempt_id=req.submission_attempt_id,
                            milestone_type=req.milestone_type,
                            status=req.status,
                            scheduled_for=scheduled_for,
                            completed_at=completed_at,
                        )
                    )
                logger.info(
                    "activity.ok name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    req.inspection_milestone_id,
                )
                return req.inspection_milestone_id
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(InspectionMilestone, req.inspection_milestone_id)
            if existing is None:
                raise RuntimeError(
                    f"inspection_milestones insert raced but row not found for inspection_milestone_id={req.inspection_milestone_id}"
                )
            logger.info(
                "activity.ok name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                req.inspection_milestone_id,
            )
            return req.inspection_milestone_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_inspection_milestone workflow_id=%s run_id=%s case_id=%s inspection_milestone_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.inspection_milestone_id,
            type(exc).__name__,
        )
        raise

__all__ = [
    "persist_approval_record",
    "persist_correction_task",
    "persist_inspection_milestone",
    "persist_resubmission_package",
]
