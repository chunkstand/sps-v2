from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
import ulid
from sqlalchemy.orm import Session

from sps.db.models import AdminSourceRuleIntent, AdminSourceRuleReview, SourceRule

APPROVED_OUTCOME = "APPROVED"


class IntentNotFoundError(Exception):
    def __init__(self, intent_id: str) -> None:
        super().__init__(f"intent_not_found:{intent_id}")
        self.intent_id = intent_id


class ReviewRequiredError(Exception):
    def __init__(self, intent_id: str) -> None:
        super().__init__(f"review_required:{intent_id}")
        self.intent_id = intent_id


class ReviewIdempotencyConflictError(Exception):
    def __init__(self, idempotency_key: str, review_id: str | None = None) -> None:
        message = f"review_idempotency_conflict:{idempotency_key}"
        if review_id:
            message = f"{message}:{review_id}"
        super().__init__(message)
        self.idempotency_key = idempotency_key
        self.review_id = review_id


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def load_intent(db: Session, intent_id: str) -> AdminSourceRuleIntent:
    row = db.get(AdminSourceRuleIntent, intent_id)
    if row is None:
        raise IntentNotFoundError(intent_id)
    return row


def load_review_by_idempotency_key(
    db: Session,
    idempotency_key: str,
) -> AdminSourceRuleReview | None:
    return (
        db.query(AdminSourceRuleReview)
        .filter(AdminSourceRuleReview.idempotency_key == idempotency_key)
        .one_or_none()
    )


def require_approved_review(db: Session, intent_id: str) -> AdminSourceRuleReview:
    row = (
        db.query(AdminSourceRuleReview)
        .filter(
            AdminSourceRuleReview.intent_id == intent_id,
            sa.func.upper(AdminSourceRuleReview.decision_outcome) == APPROVED_OUTCOME,
        )
        .order_by(AdminSourceRuleReview.reviewed_at.desc())
        .first()
    )
    if row is None:
        raise ReviewRequiredError(intent_id)
    return row


def upsert_source_rule(
    db: Session,
    *,
    intent: AdminSourceRuleIntent,
    applied_at: dt.datetime | None = None,
) -> SourceRule:
    now = applied_at or _utcnow()
    row = db.query(SourceRule).filter(SourceRule.rule_scope == intent.rule_scope).one_or_none()
    if row is None:
        row = SourceRule(
            source_rule_id=f"SR-{ulid.new()}",
            rule_scope=intent.rule_scope,
            rule_payload=intent.rule_payload,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.rule_payload = intent.rule_payload
        row.updated_at = now
    return row
