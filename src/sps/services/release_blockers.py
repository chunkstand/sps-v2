from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from sps.db.queries.release_blockers import (
    get_open_blocking_contradictions,
    get_open_blocking_dissents,
)


class ContradictionBlockerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contradiction_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    resolution_status: str = Field(min_length=1)
    blocking_effect: bool
    created_at: dt.datetime | None = None


class DissentBlockerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dissent_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    linked_review_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    resolution_state: str = Field(min_length=1)
    created_at: dt.datetime | None = None


class ReleaseBlockersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: dt.datetime
    contradictions: list[ContradictionBlockerResponse]
    dissents: list[DissentBlockerResponse]
    blocker_count: int = Field(ge=0)


def build_release_blockers_response(
    db: Session,
    *,
    now: dt.datetime | None = None,
) -> ReleaseBlockersResponse:
    snapshot_time = now or dt.datetime.now(tz=dt.UTC)

    contradictions = get_open_blocking_contradictions(db)
    dissents = get_open_blocking_dissents(db)

    contradiction_items = [
        ContradictionBlockerResponse(
            contradiction_id=row.contradiction_id,
            case_id=row.case_id,
            scope=row.scope,
            resolution_status=row.resolution_status,
            blocking_effect=row.blocking_effect,
            created_at=row.created_at,
        )
        for row in contradictions
    ]

    dissent_items = [
        DissentBlockerResponse(
            dissent_id=row.dissent_id,
            case_id=row.case_id,
            linked_review_id=row.linked_review_id,
            scope=row.scope,
            resolution_state=row.resolution_state,
            created_at=row.created_at,
        )
        for row in dissents
    ]

    return ReleaseBlockersResponse(
        generated_at=snapshot_time,
        contradictions=contradiction_items,
        dissents=dissent_items,
        blocker_count=len(contradiction_items) + len(dissent_items),
    )
