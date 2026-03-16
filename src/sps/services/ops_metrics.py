from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from sps.db.queries.ops_metrics import (
    get_contradiction_backlog,
    get_queue_depth,
    get_stalled_review_count,
)

STALLED_REVIEW_THRESHOLD = dt.timedelta(hours=24)


class OpsMetricsResponse(BaseModel):
    """Response payload for ops dashboard metrics."""

    model_config = ConfigDict(extra="forbid")

    generated_at: dt.datetime = Field(description="UTC timestamp for the snapshot.")
    queue_depth: int = Field(ge=0)
    contradiction_backlog: int = Field(ge=0)
    stalled_review_count: int = Field(ge=0)
    stalled_review_threshold_hours: int = Field(ge=0)
    stalled_review_before: dt.datetime = Field(description="UTC cutoff for stalled review detection.")


def build_ops_metrics_response(
    db: Session,
    *,
    now: dt.datetime | None = None,
    stalled_review_threshold: dt.timedelta | None = None,
) -> OpsMetricsResponse:
    """Assemble ops dashboard metrics from the database."""
    snapshot_time = now or dt.datetime.now(tz=dt.UTC)
    threshold = stalled_review_threshold or STALLED_REVIEW_THRESHOLD
    queue_depth = get_queue_depth(db)
    contradiction_backlog = get_contradiction_backlog(db)
    stalled_review_count, stalled_review_before = get_stalled_review_count(
        db,
        now=snapshot_time,
        stalled_after=threshold,
    )

    return OpsMetricsResponse(
        generated_at=snapshot_time,
        queue_depth=queue_depth,
        contradiction_backlog=contradiction_backlog,
        stalled_review_count=stalled_review_count,
        stalled_review_threshold_hours=int(threshold.total_seconds() // 3600),
        stalled_review_before=stalled_review_before,
    )
