from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from sps.config import get_settings
from sps.db.models import DissentArtifact, ReviewDecision
from sps.db.session import get_db
from sps.guards.guard_assertions import get_normalized_business_invariants
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
    subject_author_id: str = Field(min_length=1)
    outcome: ReviewDecisionOutcome
    notes: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)

    dissent_scope: str | None = None
    dissent_rationale: str | None = None
    dissent_required_followup: str | None = None

    @model_validator(mode="after")
    def _validate_dissent_fields(self) -> "CreateReviewDecisionRequest":
        if self.outcome == ReviewDecisionOutcome.ACCEPT_WITH_DISSENT and (
            self.dissent_scope is None or self.dissent_rationale is None
        ):
            raise ValueError(
                "dissent_scope and dissent_rationale are required when outcome is ACCEPT_WITH_DISSENT"
            )
        return self


class ReviewDecisionResponse(BaseModel):
    """Response shape for created / retrieved review decisions.

    Safe to log: decision_id and idempotency_key are non-sensitive identifiers.
    dissent_artifact_id is populated for ACCEPT_WITH_DISSENT decisions so callers
    can discover the linked artifact ID without a separate query.
    """

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    case_id: str
    outcome: ReviewDecisionOutcome
    idempotency_key: str
    created: dt.datetime
    dissent_artifact_id: str | None = None


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
        dissent_artifact_id=f"DISSENT-{row.decision_id}" if row.dissent_flag else None,
    )


def _check_reviewer_independence(reviewer_id: str, subject_author_id: str) -> None:
    """Enforce reviewer independence: reviewer must not be the subject author.

    Raises HTTPException(403) when the IDs match, with stable guard/invariant IDs
    sourced from the guard-assertions registry (INV-SPS-REV-001).
    Returns None on pass (IDs differ).
    """
    if reviewer_id == subject_author_id:
        logger.warning(
            "reviewer_api.independence_denied reviewer_id=%s subject_author_id=%s guard_assertion_id=INV-SPS-REV-001",
            reviewer_id,
            subject_author_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "REVIEW_INDEPENDENCE_DENIED",
                "guard_assertion_id": "INV-SPS-REV-001",
                "normalized_business_invariants": get_normalized_business_invariants("INV-SPS-REV-001"),
            },
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

    # Independence guard — must precede any DB operation
    _check_reviewer_independence(req.reviewer_id, req.subject_author_id)

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

    # If ACCEPT_WITH_DISSENT, queue a linked DissentArtifact in the same transaction.
    # dissent_scope and dissent_rationale are guaranteed non-null by model_validator.
    if row.dissent_flag:
        # Flush the ReviewDecision row first so the FK constraint on
        # dissent_artifacts.linked_review_id is satisfied at INSERT time.
        # Without an ORM relationship(), SQLAlchemy's unit-of-work cannot infer
        # the required flush ordering from the FK column definition alone.
        db.flush()
        dissent_row = DissentArtifact(
            dissent_id=f"DISSENT-{row.decision_id}",
            linked_review_id=row.decision_id,
            case_id=row.case_id,
            scope=req.dissent_scope,
            rationale=req.dissent_rationale,
            required_followup=req.dissent_required_followup,
            resolution_state="OPEN",
            created_at=now,
        )
        db.add(dissent_row)
        logger.info(
            "reviewer_api.dissent_artifact_created dissent_id=%s linked_review_id=%s case_id=%s scope_len=%d",
            dissent_row.dissent_id,
            row.decision_id,
            row.case_id,
            len(req.dissent_scope or ""),
        )

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
