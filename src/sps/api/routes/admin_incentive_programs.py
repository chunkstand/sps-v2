from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sps.api.contracts.admin_incentive_programs import (
    AdminIncentiveProgramApplyResponse,
    AdminIncentiveProgramIntentCreateRequest,
    AdminIncentiveProgramIntentResponse,
    AdminIncentiveProgramReviewDecisionRequest,
    AdminIncentiveProgramReviewDecisionResponse,
)
from sps.audit.events import emit_audit_event
from sps.auth.identity import Identity
from sps.auth.rbac import Role, require_roles
from sps.db.models import AdminIncentiveProgramIntent, AdminIncentiveProgramReview
from sps.db.session import get_db
from sps.services import admin_incentive_programs

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-incentive-programs"])


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def _require_reviewer_only(identity: Identity = Depends(require_roles(Role.REVIEWER))) -> Identity:
    reviewer_roles = {role.lower() for role in identity.roles}
    if Role.REVIEWER.value not in reviewer_roles:
        raise HTTPException(
            status_code=403,
            detail={"error_code": "role_denied", "required_roles": [Role.REVIEWER.value]},
        )
    return identity


def _intent_row_to_response(row: AdminIncentiveProgramIntent) -> AdminIncentiveProgramIntentResponse:
    return AdminIncentiveProgramIntentResponse(
        intent_id=row.intent_id,
        program_key=row.program_key,
        status=row.status,
        created_at=row.created_at,
    )


def _review_row_to_response(row: AdminIncentiveProgramReview) -> AdminIncentiveProgramReviewDecisionResponse:
    return AdminIncentiveProgramReviewDecisionResponse(
        review_id=row.review_id,
        intent_id=row.intent_id,
        decision_outcome=row.decision_outcome,
        idempotency_key=row.idempotency_key,
        reviewed_at=row.reviewed_at,
    )


@router.post("/intents", status_code=201)
def create_admin_incentive_program_intent(
    req: AdminIncentiveProgramIntentCreateRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_roles(Role.ADMIN)),
) -> AdminIncentiveProgramIntentResponse:
    now = _utcnow()
    row = AdminIncentiveProgramIntent(
        intent_id=req.intent_id,
        program_key=req.program_key,
        program_payload=req.program_payload,
        status="PENDING_REVIEW",
        requested_by=req.requested_by,
        created_at=now,
        updated_at=now,
    )
    db.add(row)

    try:
        emit_audit_event(
            db,
            action="ADMIN_INCENTIVE_PROGRAM_INTENT_CREATED",
            actor_type="admin",
            actor_id=identity.subject,
            correlation_id=req.intent_id,
            request_id=req.intent_id,
            payload={"intent_id": req.intent_id},
            occurred_at=now,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning(
            "admin_incentive_programs.intent_conflict intent_id=%s program_key=%s error=%s",
            req.intent_id,
            req.program_key,
            str(exc),
        )
        raise HTTPException(
            status_code=409,
            detail={"error_code": "intent_conflict", "intent_id": req.intent_id},
        ) from exc

    logger.info(
        "admin_incentive_programs.intent_created intent_id=%s program_key=%s",
        req.intent_id,
        req.program_key,
    )
    return _intent_row_to_response(row)


@router.post("/reviews", status_code=201)
def record_admin_incentive_program_review(
    req: AdminIncentiveProgramReviewDecisionRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(_require_reviewer_only),
) -> AdminIncentiveProgramReviewDecisionResponse:
    now = _utcnow()
    try:
        intent = admin_incentive_programs.load_intent(db, req.intent_id)
    except admin_incentive_programs.IntentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "intent_not_found", "intent_id": exc.intent_id},
        ) from exc

    existing_review = admin_incentive_programs.load_review_by_idempotency_key(db, req.idempotency_key)
    if existing_review is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "review_idempotency_conflict",
                "review_id": existing_review.review_id,
                "idempotency_key": req.idempotency_key,
            },
        )

    if db.get(AdminIncentiveProgramReview, req.review_id) is not None:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "review_conflict", "review_id": req.review_id},
        )

    row = AdminIncentiveProgramReview(
        review_id=req.review_id,
        intent_id=req.intent_id,
        reviewer_id=req.reviewer_id,
        decision_outcome=req.decision_outcome,
        review_payload=req.review_payload,
        idempotency_key=req.idempotency_key,
        reviewed_at=now,
    )
    db.add(row)

    intent.status = req.decision_outcome.upper()
    intent.updated_at = now

    emit_audit_event(
        db,
        action="ADMIN_INCENTIVE_PROGRAM_REVIEW_RECORDED",
        actor_type="reviewer",
        actor_id=identity.subject,
        correlation_id=req.intent_id,
        request_id=f"{req.intent_id}:{req.review_id}",
        payload={
            "intent_id": req.intent_id,
            "review_id": req.review_id,
            "decision_outcome": req.decision_outcome,
            "idempotency_key": req.idempotency_key,
        },
        occurred_at=now,
    )

    db.commit()

    logger.info(
        "admin_incentive_programs.review_recorded intent_id=%s review_id=%s decision_outcome=%s",
        req.intent_id,
        req.review_id,
        req.decision_outcome,
    )
    return _review_row_to_response(row)


@router.post("/apply/{intent_id}", status_code=200)
def apply_admin_incentive_program_intent(
    intent_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_roles(Role.ADMIN)),
) -> AdminIncentiveProgramApplyResponse:
    now = _utcnow()
    try:
        intent = admin_incentive_programs.load_intent(db, intent_id)
    except admin_incentive_programs.IntentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "intent_not_found", "intent_id": exc.intent_id},
        ) from exc

    try:
        approved_review = admin_incentive_programs.require_approved_review(db, intent_id)
    except admin_incentive_programs.ReviewRequiredError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "review_required", "intent_id": exc.intent_id},
        ) from exc

    program = admin_incentive_programs.upsert_incentive_program(db, intent=intent, applied_at=now)

    intent.status = "APPLIED"
    intent.updated_at = now

    emit_audit_event(
        db,
        action="ADMIN_INCENTIVE_PROGRAM_APPLIED",
        actor_type="admin",
        actor_id=identity.subject,
        correlation_id=intent_id,
        request_id=f"{intent_id}:apply",
        payload={
            "intent_id": intent_id,
            "review_id": approved_review.review_id,
            "incentive_program_id": program.incentive_program_id,
        },
        occurred_at=now,
    )

    db.commit()

    logger.info(
        "admin_incentive_programs.intent_applied intent_id=%s program_key=%s incentive_program_id=%s",
        intent_id,
        intent.program_key,
        program.incentive_program_id,
    )

    return AdminIncentiveProgramApplyResponse(
        intent_id=intent_id,
        incentive_program_id=program.incentive_program_id,
        program_key=program.program_key,
        applied_at=now,
    )
