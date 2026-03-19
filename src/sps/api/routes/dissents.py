from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from sps.auth.rbac import require_reviewer_identity
from sps.db.models import DissentArtifact
from sps.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dissents"], dependencies=[Depends(require_reviewer_identity)])


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class DissentArtifactResponse(BaseModel):
    """Full dissent artifact payload.

    Safe to surface to callers. scope and rationale may contain reviewer-entered
    text; do not log field values — log only dissent_id, linked_review_id,
    case_id, resolution_state.
    """

    model_config = ConfigDict(extra="forbid")

    dissent_id: str
    linked_review_id: str
    case_id: str
    scope: str
    rationale: str
    required_followup: str | None
    resolution_state: str
    created_at: dt.datetime


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_response(row: DissentArtifact) -> DissentArtifactResponse:
    return DissentArtifactResponse(
        dissent_id=row.dissent_id,
        linked_review_id=row.linked_review_id,
        case_id=row.case_id,
        scope=row.scope,
        rationale=row.rationale,
        required_followup=row.required_followup,
        resolution_state=row.resolution_state,
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{dissent_id}",
    status_code=200,
)
def get_dissent_artifact(
    dissent_id: str,
    db: Session = Depends(get_db),
) -> DissentArtifactResponse:
    """Read a DissentArtifact by ID.

    Returns 200 with full artifact fields when found, 404 when not found.

    Inspection surface: callers can discover the dissent_id from the
    ReviewDecisionResponse.dissent_artifact_id field on the POST response.

    Observability:
      - 404 detail includes dissent_id to aid log correlation.
      - Full artifact shape (excluding scope/rationale values) is loggable.
    """
    row = db.get(DissentArtifact, dissent_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "dissent_id": dissent_id},
        )
    return _row_to_response(row)
