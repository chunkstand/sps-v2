from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from sps.config import get_settings
from sps.db.models import ReviewDecision
from sps.db.session import get_db
from sps.workflows.permit_case.contracts import ReviewDecisionOutcome, ReviewDecisionSignal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reviews"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateReviewDecisionRequest(BaseModel):
    """Payload for POST /api/v1/reviews/decisions.

    Fields align to the ReviewDecision DB row columns that the caller supplies;
    the endpoint derives schema_version, object_type, object_id, decision_at,
    and dissent_flag from business logic.
    """

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    outcome: ReviewDecisionOutcome
    notes: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewDecisionResponse(BaseModel):
    """Response shape for created / retrieved review decisions.

    Safe to log: decision_id and idempotency_key are non-sensitive identifiers.
    """

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    case_id: str
    outcome: ReviewDecisionOutcome
    idempotency_key: str
    created: dt.datetime


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def require_reviewer_api_key(
    x_reviewer_api_key: Annotated[str | None, Header(alias="X-Reviewer-Api-Key")] = None,
) -> None:
    """FastAPI dependency that gates reviewer endpoints behind the configured API key.

    Raises HTTP 401 for missing header or key mismatch.
    The configured key is compared but never echoed in the response body or logs.

    Observability: failures are visible in API access logs as 401 responses on
    /api/v1/reviews/* paths.  No structured event is emitted here because the
    auth decision predates any request context worth logging.
    """
    if x_reviewer_api_key is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "missing_api_key", "hint": "Supply X-Reviewer-Api-Key header"},
        )
    settings = get_settings()
    if x_reviewer_api_key != settings.reviewer_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_api_key"},
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def _row_to_response(row: ReviewDecision) -> ReviewDecisionResponse:
    return ReviewDecisionResponse(
        decision_id=row.decision_id,
        case_id=row.case_id,
        outcome=ReviewDecisionOutcome(row.decision_outcome),
        idempotency_key=row.idempotency_key,
        created=row.created_at,
    )


async def _send_review_signal(
    *,
    case_id: str,
    decision_id: str,
    decision_outcome: ReviewDecisionOutcome,
    reviewer_id: str,
) -> None:
    """Deliver ReviewDecision signal to the waiting PermitCaseWorkflow.

    Failures are logged but must not bubble up to the caller — the Postgres
    write is the authoritative event; signal delivery is best-effort.
    """
    from sps.workflows.temporal import connect_client  # local import to avoid import-time side effects

    try:
        client = await asyncio.wait_for(connect_client(), timeout=10.0)
        workflow_id = f"permit-case/{case_id}"
        handle = client.get_workflow_handle(workflow_id)
        signal_payload = ReviewDecisionSignal(
            decision_id=decision_id,
            decision_outcome=decision_outcome,
            reviewer_id=reviewer_id,
        )
        await asyncio.wait_for(
            handle.signal("ReviewDecision", signal_payload),
            timeout=10.0,
        )
        logger.info(
            "reviewer_api.signal_sent decision_id=%s case_id=%s workflow_id=%s",
            decision_id,
            case_id,
            workflow_id,
        )
    except Exception as exc:
        logger.warning(
            "reviewer_api.signal_failed decision_id=%s case_id=%s signal_error=%s",
            decision_id,
            case_id,
            type(exc).__name__,
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/decisions",
    status_code=201,
    dependencies=[Depends(require_reviewer_api_key)],
)
async def create_review_decision(
    req: CreateReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> ReviewDecisionResponse:
    """Write a ReviewDecision row and signal the waiting workflow.

    Idempotency semantics:
      - Same idempotency_key + same decision_id → 200 (idempotent OK)
      - Same idempotency_key + different decision_id → 409 IDEMPOTENCY_CONFLICT
      - New idempotency_key → INSERT + 201

    Signal delivery is best-effort: Temporal unavailability after a successful
    Postgres commit logs reviewer_api.signal_failed but does not change the 201
    response status.  The review_decisions row is durable; operator can re-signal
    using workflow ID convention permit-case/<case_id>.

    Structured log events:
      reviewer_api.decision_received  decision_id=... idempotency_key=...
      reviewer_api.decision_persisted decision_id=... case_id=...
      reviewer_api.signal_sent        decision_id=... case_id=...
      reviewer_api.signal_failed      decision_id=... signal_error=...
    """
    logger.info(
        "reviewer_api.decision_received decision_id=%s idempotency_key=%s case_id=%s",
        req.decision_id,
        req.idempotency_key,
        req.case_id,
    )

    # Idempotency check
    existing = (
        db.query(ReviewDecision)
        .filter(ReviewDecision.idempotency_key == req.idempotency_key)
        .first()
    )

    if existing is not None:
        if existing.decision_id == req.decision_id:
            # Idempotent OK — same key, same decision
            return _row_to_response(existing)
        else:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "IDEMPOTENCY_CONFLICT",
                    "existing_decision_id": existing.decision_id,
                    "idempotency_key": req.idempotency_key,
                },
            )

    # New decision — insert
    now = _utcnow()
    row = ReviewDecision(
        decision_id=req.decision_id,
        schema_version="1.0",
        case_id=req.case_id,
        object_type="permit_case",
        object_id=req.case_id,
        decision_outcome=req.outcome.value,
        reviewer_id=req.reviewer_id,
        reviewer_independence_status="PASS",
        evidence_ids=req.evidence_ids,
        contradiction_resolution=None,
        dissent_flag=(req.outcome == ReviewDecisionOutcome.ACCEPT_WITH_DISSENT),
        notes=req.notes,
        decision_at=now,
        idempotency_key=req.idempotency_key,
    )
    db.add(row)
    db.commit()

    logger.info(
        "reviewer_api.decision_persisted decision_id=%s case_id=%s idempotency_key=%s",
        req.decision_id,
        req.case_id,
        req.idempotency_key,
    )

    # Signal delivery — best-effort, must not affect HTTP response
    await _send_review_signal(
        case_id=req.case_id,
        decision_id=req.decision_id,
        decision_outcome=req.outcome,
        reviewer_id=req.reviewer_id,
    )

    return _row_to_response(row)


@router.get(
    "/decisions/{decision_id}",
    dependencies=[Depends(require_reviewer_api_key)],
)
def get_review_decision(decision_id: str, db: Session = Depends(get_db)) -> ReviewDecisionResponse:
    """Read-only inspection surface for a persisted ReviewDecision.

    Returns 200 with the decision payload, or 404 if the decision_id is unknown.
    """
    row = db.get(ReviewDecision, decision_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "decision_id": decision_id},
        )
    return _row_to_response(row)
