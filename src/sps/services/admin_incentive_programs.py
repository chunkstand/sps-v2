from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
import ulid
from sqlalchemy.orm import Session

from sps.db.models import AdminIncentiveProgramIntent, AdminIncentiveProgramReview, IncentiveProgram

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


def load_intent(db: Session, intent_id: str) -> AdminIncentiveProgramIntent:
    row = db.get(AdminIncentiveProgramIntent, intent_id)
    if row is None:
        raise IntentNotFoundError(intent_id)
    return row


def load_review_by_idempotency_key(
    db: Session,
    idempotency_key: str,
) -> AdminIncentiveProgramReview | None:
    return (
        db.query(AdminIncentiveProgramReview)
        .filter(AdminIncentiveProgramReview.idempotency_key == idempotency_key)
        .one_or_none()
    )


def require_approved_review(db: Session, intent_id: str) -> AdminIncentiveProgramReview:
    row = (
        db.query(AdminIncentiveProgramReview)
        .filter(
            AdminIncentiveProgramReview.intent_id == intent_id,
            sa.func.upper(AdminIncentiveProgramReview.decision_outcome) == APPROVED_OUTCOME,
        )
        .order_by(AdminIncentiveProgramReview.reviewed_at.desc())
        .first()
    )
    if row is None:
        raise ReviewRequiredError(intent_id)
    return row


def upsert_incentive_program(
    db: Session,
    *,
    intent: AdminIncentiveProgramIntent,
    applied_at: dt.datetime | None = None,
) -> IncentiveProgram:
    now = applied_at or _utcnow()
    row = (
        db.query(IncentiveProgram)
        .filter(IncentiveProgram.program_key == intent.program_key)
        .one_or_none()
    )
    if row is None:
        row = IncentiveProgram(
            incentive_program_id=f"IP-{ulid.new()}",
            program_key=intent.program_key,
            program_payload=intent.program_payload,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.program_payload = intent.program_payload
        row.updated_at = now
    return row
