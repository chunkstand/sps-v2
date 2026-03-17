from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sps.api.contracts.admin_source_rules import (
    AdminSourceRuleApplyResponse,
    AdminSourceRuleIntentCreateRequest,
    AdminSourceRuleIntentResponse,
    AdminSourceRuleReviewDecisionRequest,
    AdminSourceRuleReviewDecisionResponse,
)
from sps.audit.events import emit_audit_event
from sps.auth.identity import Identity
from sps.auth.rbac import Role, require_roles
from sps.db.models import AdminSourceRuleIntent, AdminSourceRuleReview
from sps.db.session import get_db
from sps.services import admin_source_rules

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-source-rules"])


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


def _intent_row_to_response(row: AdminSourceRuleIntent) -> AdminSourceRuleIntentResponse:
    return AdminSourceRuleIntentResponse(
        intent_id=row.intent_id,
        rule_scope=row.rule_scope,
        status=row.status,
        created_at=row.created_at,
    )


def _review_row_to_response(row: AdminSourceRuleReview) -> AdminSourceRuleReviewDecisionResponse:
    return AdminSourceRuleReviewDecisionResponse(
        review_id=row.review_id,
        intent_id=row.intent_id,
        decision_outcome=row.decision_outcome,
        idempotency_key=row.idempotency_key,
        reviewed_at=row.reviewed_at,
    )


@router.post("/intents", status_code=201)
def create_admin_source_rule_intent(
    req: AdminSourceRuleIntentCreateRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_roles(Role.ADMIN)),
) -> AdminSourceRuleIntentResponse:
    now = _utcnow()
    row = AdminSourceRuleIntent(
        intent_id=req.intent_id,
        rule_scope=req.rule_scope,
        rule_payload=req.rule_payload,
        status="PENDING_REVIEW",
        requested_by=req.requested_by,
        created_at=now,
        updated_at=now,
    )
    db.add(row)

    try:
        emit_audit_event(
            db,
            action="ADMIN_SOURCE_RULE_INTENT_CREATED",
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
            "admin_source_rules.intent_conflict intent_id=%s rule_scope=%s error=%s",
            req.intent_id,
            req.rule_scope,
            str(exc),
        )
        raise HTTPException(
            status_code=409,
            detail={"error_code": "intent_conflict", "intent_id": req.intent_id},
        ) from exc

    logger.info(
        "admin_source_rules.intent_created intent_id=%s rule_scope=%s",
        req.intent_id,
        req.rule_scope,
    )
    return _intent_row_to_response(row)


@router.post("/reviews", status_code=201)
def record_admin_source_rule_review(
    req: AdminSourceRuleReviewDecisionRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(_require_reviewer_only),
) -> AdminSourceRuleReviewDecisionResponse:
    now = _utcnow()
    try:
        intent = admin_source_rules.load_intent(db, req.intent_id)
    except admin_source_rules.IntentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "intent_not_found", "intent_id": exc.intent_id},
        ) from exc

    existing_review = admin_source_rules.load_review_by_idempotency_key(db, req.idempotency_key)
    if existing_review is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "review_idempotency_conflict",
                "review_id": existing_review.review_id,
                "idempotency_key": req.idempotency_key,
            },
        )

    if db.get(AdminSourceRuleReview, req.review_id) is not None:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "review_conflict", "review_id": req.review_id},
        )

    row = AdminSourceRuleReview(
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
        action="ADMIN_SOURCE_RULE_REVIEW_RECORDED",
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
        "admin_source_rules.review_recorded intent_id=%s review_id=%s decision_outcome=%s",
        req.intent_id,
        req.review_id,
        req.decision_outcome,
    )
    return _review_row_to_response(row)


@router.post("/apply/{intent_id}", status_code=200)
def apply_admin_source_rule_intent(
    intent_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_roles(Role.ADMIN)),
) -> AdminSourceRuleApplyResponse:
    now = _utcnow()
    try:
        intent = admin_source_rules.load_intent(db, intent_id)
    except admin_source_rules.IntentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "intent_not_found", "intent_id": exc.intent_id},
        ) from exc

    try:
        approved_review = admin_source_rules.require_approved_review(db, intent_id)
    except admin_source_rules.ReviewRequiredError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "review_required", "intent_id": exc.intent_id},
        ) from exc

    source_rule = admin_source_rules.upsert_source_rule(db, intent=intent, applied_at=now)

    intent.status = "APPLIED"
    intent.updated_at = now

    emit_audit_event(
        db,
        action="ADMIN_SOURCE_RULE_APPLIED",
        actor_type="admin",
        actor_id=identity.subject,
        correlation_id=intent_id,
        request_id=f"{intent_id}:apply",
        payload={
            "intent_id": intent_id,
            "review_id": approved_review.review_id,
            "source_rule_id": source_rule.source_rule_id,
        },
        occurred_at=now,
    )

    db.commit()

    logger.info(
        "admin_source_rules.intent_applied intent_id=%s rule_scope=%s source_rule_id=%s",
        intent_id,
        intent.rule_scope,
        source_rule.source_rule_id,
    )

    return AdminSourceRuleApplyResponse(
        intent_id=intent_id,
        source_rule_id=source_rule.source_rule_id,
        rule_scope=source_rule.rule_scope,
        applied_at=now,
    )
