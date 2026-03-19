from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sps.auth.rbac import require_reviewer_identity
from sps.db.models import ContradictionArtifact
from sps.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["contradictions"],
    dependencies=[Depends(require_reviewer_identity)],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateContradictionRequest(BaseModel):
    """Payload for POST /api/v1/contradictions."""

    model_config = ConfigDict(extra="forbid")

    contradiction_id: str
    case_id: str
    scope: str
    source_a: str
    source_b: str
    ranking_relation: str
    blocking_effect: bool


class ResolveContradictionRequest(BaseModel):
    """Payload for POST /api/v1/contradictions/{contradiction_id}/resolve."""

    model_config = ConfigDict(extra="forbid")

    resolved_by: str


class ContradictionResponse(BaseModel):
    """Response shape for contradiction artifact reads and creates."""

    model_config = ConfigDict(extra="forbid")

    contradiction_id: str
    case_id: str
    scope: str
    source_a: str
    source_b: str
    ranking_relation: str
    blocking_effect: bool
    resolution_status: str
    resolved_at: dt.datetime | None
    resolved_by: str | None
    created_at: dt.datetime


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def _row_to_response(row: ContradictionArtifact) -> ContradictionResponse:
    return ContradictionResponse(
        contradiction_id=row.contradiction_id,
        case_id=row.case_id,
        scope=row.scope,
        source_a=row.source_a,
        source_b=row.source_b,
        ranking_relation=row.ranking_relation,
        blocking_effect=row.blocking_effect,
        resolution_status=row.resolution_status,
        resolved_at=row.resolved_at,
        resolved_by=row.resolved_by,
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    status_code=201,
)
def create_contradiction(
    req: CreateContradictionRequest,
    db: Session = Depends(get_db),
) -> ContradictionResponse:
    """Create a ContradictionArtifact row with resolution_status='OPEN'.

    Returns 201 on success, 409 if contradiction_id already exists.

    Structured log events:
      contradiction_api.create  contradiction_id=... case_id=... blocking_effect=...
    """
    row = ContradictionArtifact(
        contradiction_id=req.contradiction_id,
        case_id=req.case_id,
        scope=req.scope,
        source_a=req.source_a,
        source_b=req.source_b,
        ranking_relation=req.ranking_relation,
        blocking_effect=req.blocking_effect,
        resolution_status="OPEN",
        resolved_at=None,
        resolved_by=None,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "error": "CONTRADICTION_ALREADY_EXISTS",
                "contradiction_id": req.contradiction_id,
            },
        )

    logger.info(
        "contradiction_api.create contradiction_id=%s case_id=%s blocking_effect=%s",
        req.contradiction_id,
        req.case_id,
        req.blocking_effect,
    )
    return _row_to_response(row)


@router.post(
    "/{contradiction_id}/resolve",
    status_code=200,
)
def resolve_contradiction(
    contradiction_id: str,
    req: ResolveContradictionRequest,
    db: Session = Depends(get_db),
) -> ContradictionResponse:
    """Resolve an open ContradictionArtifact.

    Returns 200 on OPEN → RESOLVED, 409 if already resolved, 404 if unknown.

    Structured log events:
      contradiction_api.resolve  contradiction_id=... case_id=...
    """
    row = db.get(ContradictionArtifact, contradiction_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "contradiction_id": contradiction_id},
        )

    if row.resolution_status != "OPEN":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "ALREADY_RESOLVED",
                "contradiction_id": contradiction_id,
                "resolution_status": row.resolution_status,
            },
        )

    row.resolution_status = "RESOLVED"
    row.resolved_at = _utcnow()
    row.resolved_by = req.resolved_by
    db.commit()

    logger.info(
        "contradiction_api.resolve contradiction_id=%s case_id=%s",
        contradiction_id,
        row.case_id,
    )
    return _row_to_response(row)


@router.get(
    "/{contradiction_id}",
    status_code=200,
)
def get_contradiction(
    contradiction_id: str,
    db: Session = Depends(get_db),
) -> ContradictionResponse:
    """Read a ContradictionArtifact by ID.

    Returns 200 with full ContradictionResponse, or 404 if unknown.

    Inspection surface: returns full row including resolution_status, resolved_at, resolved_by.
    """
    row = db.get(ContradictionArtifact, contradiction_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "contradiction_id": contradiction_id},
        )
    return _row_to_response(row)
