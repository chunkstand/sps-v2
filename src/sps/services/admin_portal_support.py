from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
import ulid
from sqlalchemy.orm import Session

from sps.db.models import AdminPortalSupportIntent, AdminPortalSupportReview, PortalSupportMetadata

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


def load_intent(db: Session, intent_id: str) -> AdminPortalSupportIntent:
    row = db.get(AdminPortalSupportIntent, intent_id)
    if row is None:
        raise IntentNotFoundError(intent_id)
    return row


def load_review_by_idempotency_key(
    db: Session,
    idempotency_key: str,
) -> AdminPortalSupportReview | None:
    return (
        db.query(AdminPortalSupportReview)
        .filter(AdminPortalSupportReview.idempotency_key == idempotency_key)
        .one_or_none()
    )


def require_approved_review(db: Session, intent_id: str) -> AdminPortalSupportReview:
    row = (
        db.query(AdminPortalSupportReview)
        .filter(
            AdminPortalSupportReview.intent_id == intent_id,
            sa.func.upper(AdminPortalSupportReview.decision_outcome) == APPROVED_OUTCOME,
        )
        .order_by(AdminPortalSupportReview.reviewed_at.desc())
        .first()
    )
    if row is None:
        raise ReviewRequiredError(intent_id)
    return row


def upsert_portal_support_metadata(
    db: Session,
    *,
    intent: AdminPortalSupportIntent,
    applied_at: dt.datetime | None = None,
) -> PortalSupportMetadata:
    now = applied_at or _utcnow()
    row = (
        db.query(PortalSupportMetadata)
        .filter(PortalSupportMetadata.portal_family == intent.portal_family)
        .one_or_none()
    )
    if row is None:
        row = PortalSupportMetadata(
            portal_support_metadata_id=f"PSM-{ulid.new()}",
            portal_family=intent.portal_family,
            support_level=intent.requested_support_level,
            metadata_payload=intent.intent_payload,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.support_level = intent.requested_support_level
        row.metadata_payload = intent.intent_payload
        row.updated_at = now
    return row
