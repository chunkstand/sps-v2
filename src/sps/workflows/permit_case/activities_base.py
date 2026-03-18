from __future__ import annotations

import datetime as dt

from temporalio import activity

from sps.db.models import EmergencyRecord, PermitCase, ReviewDecision
from sps.db.session import get_sessionmaker
from sps.workflows.permit_case.activities_impl import (
    persist_compliance_evaluation,
    persist_external_status_event,
    persist_incentive_assessment,
    persist_jurisdiction_resolutions,
    persist_requirement_sets,
)
from sps.workflows.permit_case.activities_shared import logger, safe_temporal_ids
from sps.workflows.permit_case.contracts import CaseState, PermitCaseStateSnapshot


@activity.defn
def ensure_permit_case_exists(case_id: str) -> bool:
    info = activity.info()
    logger.info(
        "activity.start name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s",
        info.workflow_id,
        info.workflow_run_id,
        case_id,
    )

    SessionLocal = get_sessionmaker()
    created = False
    try:
        with SessionLocal() as session:
            existing = session.get(PermitCase, case_id)
            if existing is None:
                created = True
                session.add(
                    PermitCase(
                        case_id=case_id,
                        tenant_id="tenant-local",
                        project_id=f"project-{case_id}",
                        case_state=CaseState.REVIEW_PENDING.value,
                        review_state="PENDING",
                        submission_mode="AUTOMATED",
                        portal_support_level="FULLY_SUPPORTED",
                        current_package_id=None,
                        current_release_profile="default",
                        legal_hold=False,
                        closure_reason=None,
                    )
                )
                session.commit()

        logger.info(
            "activity.ok name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s created=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            created,
        )
        return created
    except Exception as exc:
        logger.exception(
            "activity.error name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s exc_type=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def fetch_permit_case_state(case_id: str) -> PermitCaseStateSnapshot:
    workflow_id, run_id = safe_temporal_ids()
    logger.info(
        "activity.start name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s",
        workflow_id,
        run_id,
        case_id,
    )

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            case = session.get(PermitCase, case_id)
            if case is None:
                raise LookupError(f"permit_cases row not found for case_id={case_id}")

            snapshot = PermitCaseStateSnapshot(
                case_id=case.case_id,
                case_state=CaseState(case.case_state),
                project_id=case.project_id,
            )

        logger.info(
            "activity.ok name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s case_state=%s",
            workflow_id,
            run_id,
            case_id,
            snapshot.case_state,
        )
        return snapshot
    except Exception as exc:
        logger.exception(
            "activity.error name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s exc_type=%s",
            workflow_id,
            run_id,
            case_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def validate_emergency_artifact(emergency_id: str) -> str:
    workflow_id, run_id = safe_temporal_ids()
    logger.info(
        "activity.start name=validate_emergency_artifact workflow_id=%s run_id=%s emergency_id=%s",
        workflow_id,
        run_id,
        emergency_id,
    )

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            record = session.get(EmergencyRecord, emergency_id)
            if record is None:
                raise LookupError(f"emergency_records row not found for emergency_id={emergency_id}")

            expires_at = record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.UTC)

            if expires_at <= dt.datetime.now(dt.UTC):
                raise ValueError(f"emergency_id={emergency_id} expired at {expires_at.isoformat()}")

        logger.info(
            "activity.ok name=validate_emergency_artifact workflow_id=%s run_id=%s emergency_id=%s",
            workflow_id,
            run_id,
            emergency_id,
        )
        return emergency_id
    except Exception as exc:
        logger.exception(
            "activity.error name=validate_emergency_artifact workflow_id=%s run_id=%s emergency_id=%s exc_type=%s",
            workflow_id,
            run_id,
            emergency_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def validate_reviewer_confirmation(reviewer_confirmation_id: str) -> str:
    workflow_id, run_id = safe_temporal_ids()
    logger.info(
        "activity.start name=validate_reviewer_confirmation workflow_id=%s run_id=%s reviewer_confirmation_id=%s",
        workflow_id,
        run_id,
        reviewer_confirmation_id,
    )

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            decision = session.get(ReviewDecision, reviewer_confirmation_id)
            if decision is None:
                raise LookupError(
                    "review_decisions row not found for reviewer_confirmation_id=%s" % reviewer_confirmation_id
                )

        logger.info(
            "activity.ok name=validate_reviewer_confirmation workflow_id=%s run_id=%s reviewer_confirmation_id=%s",
            workflow_id,
            run_id,
            reviewer_confirmation_id,
        )
        return reviewer_confirmation_id
    except Exception as exc:
        logger.exception(
            "activity.error name=validate_reviewer_confirmation workflow_id=%s run_id=%s reviewer_confirmation_id=%s exc_type=%s",
            workflow_id,
            run_id,
            reviewer_confirmation_id,
            type(exc).__name__,
        )
        raise

__all__ = [
    "ensure_permit_case_exists",
    "fetch_permit_case_state",
    "persist_compliance_evaluation",
    "persist_external_status_event",
    "persist_incentive_assessment",
    "persist_jurisdiction_resolutions",
    "persist_requirement_sets",
    "validate_emergency_artifact",
    "validate_reviewer_confirmation",
]
