from __future__ import annotations

import datetime as dt
import logging

import ulid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sps.auth.identity import Identity
from sps.auth.rbac import Role, require_roles
from sps.db.models import EmergencyRecord
from sps.db.session import get_db

from sps.api.contracts.emergencies import CreateEmergencyRequest, EmergencyResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["emergencies"],
    dependencies=[Depends(require_roles(Role.ESCALATION_OWNER))],
)

# Maximum emergency duration in hours (24 hours)
MAX_EMERGENCY_DURATION_HOURS = 24


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def _row_to_response(row: EmergencyRecord) -> EmergencyResponse:
    return EmergencyResponse(
        emergency_id=row.emergency_id,
        case_id=row.case_id,
        incident_id=row.incident_id,
        scope=row.scope,
        declared_by=row.declared_by,
        started_at=row.started_at,
        expires_at=row.expires_at,
        cleanup_due_at=row.cleanup_due_at,
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    status_code=201,
)
def create_emergency(
    req: CreateEmergencyRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_roles(Role.ESCALATION_OWNER)),
) -> EmergencyResponse:
    """Create an EmergencyRecord with 24-hour max duration enforcement.

    Returns 201 on success, 422 if duration exceeds 24h, 409 if emergency_id conflict.

    Structured log events:
      emergency_api.emergency_declared  emergency_id=... case_id=... scope=... expires_at=...
      emergency_api.emergency_creation_failed  case_id=... reason=...
    """
    # Validate duration if provided
    duration_hours = req.duration_hours if req.duration_hours is not None else MAX_EMERGENCY_DURATION_HOURS
    if duration_hours > MAX_EMERGENCY_DURATION_HOURS:
        logger.warning(
            "emergency_api.emergency_creation_failed case_id=%s reason=duration_exceeds_limit requested_hours=%s",
            req.case_id,
            duration_hours,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_DURATION",
                "message": "Emergency duration cannot exceed 24 hours",
                "requested_hours": duration_hours,
                "max_hours": MAX_EMERGENCY_DURATION_HOURS,
            },
        )

    # Generate idempotent emergency_id
    emergency_id = f"EMERG-{ulid.new()}"

    # Compute time bounds
    started_at = _utcnow()
    expires_at = started_at + dt.timedelta(hours=duration_hours)
    cleanup_due_at = expires_at + dt.timedelta(hours=24)  # 24 hours after expiry for cleanup

    # Persist EmergencyRecord
    row = EmergencyRecord(
        emergency_id=emergency_id,
        incident_id=req.incident_id,
        case_id=req.case_id,
        scope=req.scope,
        declared_by=identity.subject,
        started_at=started_at,
        expires_at=expires_at,
        allowed_bypasses=req.allowed_bypasses if req.allowed_bypasses else None,
        forbidden_bypasses=req.forbidden_bypasses if req.forbidden_bypasses else None,
        cleanup_due_at=cleanup_due_at,
    )

    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning(
            "emergency_api.emergency_creation_failed case_id=%s reason=persistence_error error=%s",
            req.case_id,
            str(exc),
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": "EMERGENCY_CONFLICT",
                "emergency_id": emergency_id,
            },
        ) from exc

    # Emit structured log on success
    logger.info(
        "emergency_api.emergency_declared emergency_id=%s case_id=%s scope=%s expires_at=%s",
        emergency_id,
        req.case_id,
        req.scope,
        expires_at.isoformat(),
    )

    return _row_to_response(row)
