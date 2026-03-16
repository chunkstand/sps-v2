from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from sps.db.models import AuditEvent


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def emit_audit_event(
    session: Session,
    *,
    action: str,
    actor_type: str,
    actor_id: str,
    correlation_id: str | None,
    request_id: str | None,
    payload: dict | None,
    occurred_at: dt.datetime | None = None,
    event_id: str | None = None,
) -> AuditEvent:
    """Persist an audit event within the caller's transaction.

    Caller owns the transaction boundary; this only stages the row.
    """

    event_timestamp = occurred_at or _utcnow()
    event_identifier = event_id or f"AUDIT-{uuid.uuid4()}"

    row = AuditEvent(
        event_id=event_identifier,
        correlation_id=correlation_id,
        request_id=request_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        payload=payload,
        occurred_at=event_timestamp,
    )
    session.add(row)
    return row
