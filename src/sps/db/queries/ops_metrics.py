from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.orm import Session

from sps.db.models import ContradictionArtifact, PermitCase


def get_queue_depth(db: Session) -> int:
    """Return count of cases currently in REVIEW_PENDING."""
    count = (
        db.query(sa.func.count(PermitCase.case_id))
        .filter(PermitCase.case_state == "REVIEW_PENDING")
        .scalar()
    )
    return int(count or 0)


def get_contradiction_backlog(db: Session) -> int:
    """Return count of open blocking contradictions."""
    count = (
        db.query(sa.func.count(ContradictionArtifact.contradiction_id))
        .filter(
            ContradictionArtifact.resolution_status == "OPEN",
            ContradictionArtifact.blocking_effect.is_(True),
        )
        .scalar()
    )
    return int(count or 0)


def get_stalled_review_count(
    db: Session,
    *,
    now: dt.datetime,
    stalled_after: dt.timedelta,
) -> tuple[int, dt.datetime]:
    """Return count of review-pending cases older than the SLA window.

    Args:
        now: Current UTC timestamp.
        stalled_after: Duration after which a review-pending case is considered stalled.

    Returns:
        (count, cutoff_timestamp)
    """
    cutoff = now - stalled_after
    count = (
        db.query(sa.func.count(PermitCase.case_id))
        .filter(
            PermitCase.case_state == "REVIEW_PENDING",
            PermitCase.updated_at <= cutoff,
        )
        .scalar()
    )
    return int(count or 0), cutoff
