from __future__ import annotations

import datetime as dt
import logging

import ulid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sps.auth.identity import Identity
from sps.auth.rbac import Role, require_roles
from sps.db.models import OverrideArtifact
from sps.db.session import get_db

from sps.api.contracts.overrides import CreateOverrideRequest, OverrideResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["overrides"],
    dependencies=[Depends(require_roles(Role.ESCALATION_OWNER))],
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def _row_to_response(row: OverrideArtifact) -> OverrideResponse:
    return OverrideResponse(
        override_id=row.override_id,
        case_id=row.case_id,
        scope=row.scope,
        approver_id=row.approver_id,
        start_at=row.start_at,
        expires_at=row.expires_at,
        affected_surfaces=row.affected_surfaces,
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    status_code=201,
)
def create_override(
    req: CreateOverrideRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_roles(Role.ESCALATION_OWNER)),
) -> OverrideResponse:
    """Create an OverrideArtifact with scope and time bounds.

    Returns 201 on success, 422 if validation fails, 409 if override_id conflict.

    Structured log events:
      override_api.override_created  override_id=... scope=... expires_at=... affected_surfaces=...
      override_api.override_creation_failed  case_id=... reason=...
    """
    # Generate idempotent override_id
    override_id = f"OVR-{ulid.new()}"

    # Compute time bounds
    start_at = _utcnow()
    expires_at = start_at + dt.timedelta(hours=req.duration_hours)

    # Persist OverrideArtifact
    row = OverrideArtifact(
        override_id=override_id,
        case_id=req.case_id,
        scope=req.scope,
        justification=req.justification,
        start_at=start_at,
        expires_at=expires_at,
        affected_surfaces=req.affected_surfaces,
        approver_id=identity.subject,
        cleanup_required=True,
    )

    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning(
            "override_api.override_creation_failed case_id=%s reason=persistence_error error=%s",
            req.case_id,
            str(exc),
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": "OVERRIDE_CONFLICT",
                "override_id": override_id,
            },
        ) from exc

    # Emit structured log on success
    logger.info(
        "override_api.override_created override_id=%s scope=%s expires_at=%s affected_surfaces=%s",
        override_id,
        req.scope,
        expires_at.isoformat(),
        req.affected_surfaces,
    )

    return _row_to_response(row)
