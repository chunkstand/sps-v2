from __future__ import annotations

import asyncio
import datetime as dt
import logging
from dataclasses import dataclass

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from sps.api.contracts.reviews import (
    EvidenceArtifactMetadataResponse,
    EvidenceSummaryResponse,
    ReviewDecisionSummaryResponse,
    ReviewerQueueItemResponse,
    ReviewerQueueResponse,
)
from sps.audit.events import emit_audit_event
from sps.auth.rbac import require_reviewer_identity
from sps.db.models import (
    DissentArtifact,
    EvidenceArtifact,
    ExternalStatusEvent,
    JurisdictionResolution,
    PermitCase,
    Project,
    RequirementSet,
    ReviewDecision,
)
from sps.db.session import get_db
from sps.guards.guard_assertions import get_normalized_business_invariants
from sps.workflows.permit_case.contracts import (
    ReviewDecisionOutcome,
    ReviewDecisionSignal,
    ReviewerIndependenceStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reviews"], dependencies=[Depends(require_reviewer_identity)])
_DEFAULT_QUEUE_LIMIT = 20
_MAX_QUEUE_LIMIT = 100


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
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def _clamp_queue_limit(limit: int) -> int:
    return min(limit, _MAX_QUEUE_LIMIT)


def _row_to_response(row: ReviewDecision) -> ReviewDecisionResponse:
    return ReviewDecisionResponse(
        decision_id=row.decision_id,
        case_id=row.case_id,
        outcome=ReviewDecisionOutcome(row.decision_outcome),
        idempotency_key=row.idempotency_key,
        created=row.created_at,
        dissent_artifact_id=f"DISSENT-{row.decision_id}" if row.dissent_flag else None,
    )


def _queue_row_to_response(case: PermitCase, project: Project) -> ReviewerQueueItemResponse:
    return ReviewerQueueItemResponse(
        case_id=case.case_id,
        project_id=case.project_id,
        case_state=case.case_state,
        review_state=case.review_state,
        submission_mode=case.submission_mode,
        portal_support_level=case.portal_support_level,
        current_release_profile=case.current_release_profile,
        legal_hold=case.legal_hold,
        created_at=case.created_at,
        updated_at=case.updated_at,
        address=project.address,
        parcel_id=project.parcel_id,
        project_type=project.project_type,
        system_size_kw=project.system_size_kw,
        battery_flag=project.battery_flag,
        service_upgrade_flag=project.service_upgrade_flag,
        trenching_flag=project.trenching_flag,
        structural_modification_flag=project.structural_modification_flag,
        roof_type=project.roof_type,
        occupancy_classification=project.occupancy_classification,
        utility_name=project.utility_name,
    )


def _artifact_row_to_response(row: EvidenceArtifact) -> EvidenceArtifactMetadataResponse:
    return EvidenceArtifactMetadataResponse(
        artifact_id=row.artifact_id,
        artifact_class=row.artifact_class,
        producing_service=row.producing_service,
        linked_case_id=row.linked_case_id,
        linked_object_id=row.linked_object_id,
        authoritativeness=row.authoritativeness,
        retention_class=row.retention_class,
        checksum=row.checksum,
        storage_uri=row.storage_uri,
        content_bytes=row.content_bytes,
        content_type=row.content_type,
        provenance=row.provenance,
        created_at=row.created_at,
        expires_at=row.expires_at,
    )


def _decision_row_to_summary(row: ReviewDecision) -> ReviewDecisionSummaryResponse:
    return ReviewDecisionSummaryResponse(
        decision_id=row.decision_id,
        outcome=row.decision_outcome,
        reviewer_id=row.reviewer_id,
        reviewer_independence_status=row.reviewer_independence_status,
        decision_at=row.decision_at,
    )


def _collect_evidence_ids(db: Session, case_id: str) -> list[str]:
    evidence_selects = [
        sa.select(JurisdictionResolution.evidence_ids).where(
            JurisdictionResolution.case_id == case_id
        ),
        sa.select(RequirementSet.evidence_ids).where(RequirementSet.case_id == case_id),
        sa.select(ReviewDecision.evidence_ids).where(ReviewDecision.case_id == case_id),
        sa.select(ExternalStatusEvent.evidence_ids).where(ExternalStatusEvent.case_id == case_id),
    ]
    union_stmt = sa.union_all(*evidence_selects)
    rows = db.execute(union_stmt).scalars().all()
    aggregated: set[str] = set()
    for entry in rows:
        if entry:
            aggregated.update(entry)
    return sorted(aggregated)


@dataclass(frozen=True)
class ReviewerIndependenceMetrics:
    window_start: dt.datetime
    window_end: dt.datetime
    total_reviews: int
    pair_total_reviews: int
    repeated_pair_reviews: int
    repeated_pair_rate: float


def _compute_reviewer_independence_metrics(
    db: Session,
    reviewer_id: str,
    subject_author_id: str,
    decision_at: dt.datetime,
) -> ReviewerIndependenceMetrics:
    window_end = decision_at
    window_start = window_end - dt.timedelta(days=90)

    total_reviews = (
        db.query(sa.func.count(ReviewDecision.decision_id))
        .filter(ReviewDecision.decision_at >= window_start)
        .scalar()
    )
    pair_total_reviews = (
        db.query(sa.func.count(ReviewDecision.decision_id))
        .filter(ReviewDecision.decision_at >= window_start)
        .filter(ReviewDecision.reviewer_id == reviewer_id)
        .filter(ReviewDecision.subject_author_id == subject_author_id)
        .scalar()
    )

    if total_reviews is None or pair_total_reviews is None:
        raise RuntimeError("independence_metrics_unavailable")

    total_reviews = int(total_reviews) + 1
    pair_total_reviews = int(pair_total_reviews) + 1
    repeated_pair_reviews = max(pair_total_reviews - 1, 0)

    if total_reviews <= 0 or pair_total_reviews < 0 or pair_total_reviews > total_reviews:
        raise RuntimeError("independence_metrics_invalid")

    repeated_pair_rate = repeated_pair_reviews / total_reviews

    return ReviewerIndependenceMetrics(
        window_start=window_start,
        window_end=window_end,
        total_reviews=total_reviews,
        pair_total_reviews=pair_total_reviews,
        repeated_pair_reviews=repeated_pair_reviews,
        repeated_pair_rate=repeated_pair_rate,
    )


def _emit_independence_log(
    event_name: str,
    *,
    reviewer_id: str,
    subject_author_id: str,
    metrics: ReviewerIndependenceMetrics,
    status: ReviewerIndependenceStatus | None = None,
    reason: str | None = None,
) -> None:
    logger.warning(
        "%s reviewer_id=%s subject_author_id=%s total_reviews=%d pair_total_reviews=%d repeated_pair_reviews=%d "
        "repeated_pair_rate=%.4f window_start=%s window_end=%s status=%s reason=%s",
        event_name,
        reviewer_id,
        subject_author_id,
        metrics.total_reviews,
        metrics.pair_total_reviews,
        metrics.repeated_pair_reviews,
        metrics.repeated_pair_rate,
        metrics.window_start.isoformat(),
        metrics.window_end.isoformat(),
        status.value if status else None,
        reason,
    )


def _independence_status_for_rate(rate: float) -> ReviewerIndependenceStatus:
    if rate > 0.50:
        return ReviewerIndependenceStatus.BLOCKED
    if rate > 0.35:
        return ReviewerIndependenceStatus.ESCALATION_REQUIRED
    if rate > 0.25:
        return ReviewerIndependenceStatus.WARNING
    return ReviewerIndependenceStatus.PASS


def _check_reviewer_independence(
    db: Session,
    reviewer_id: str,
    subject_author_id: str,
    decision_at: dt.datetime,
) -> ReviewerIndependenceStatus:
    """Enforce reviewer independence and rolling-quarter threshold policy.

    Raises HTTPException(403) when the IDs match or thresholds are blocked, with
    stable guard/invariant IDs sourced from the guard-assertions registry
    (INV-SPS-REV-001). Returns the computed ReviewerIndependenceStatus on pass
    or when warning/escalation thresholds are triggered.
    """
    if reviewer_id == subject_author_id:
        logger.warning(
            "reviewer_api.independence_denied reviewer_id=%s subject_author_id=%s guard_assertion_id=INV-SPS-REV-001",
            reviewer_id,
            subject_author_id,
        )
        logger.warning(
            "reviewer_api.independence_blocked reviewer_id=%s subject_author_id=%s reason=self_approval guard_assertion_id=INV-SPS-REV-001",
            reviewer_id,
            subject_author_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "REVIEW_INDEPENDENCE_DENIED",
                "guard_assertion_id": "INV-SPS-REV-001",
                "normalized_business_invariants": get_normalized_business_invariants(
                    "INV-SPS-REV-001"
                ),
                "blocked_reason": "SELF_APPROVAL",
            },
        )

    try:
        metrics = _compute_reviewer_independence_metrics(
            db=db,
            reviewer_id=reviewer_id,
            subject_author_id=subject_author_id,
            decision_at=decision_at,
        )
    except Exception as exc:
        logger.warning(
            "reviewer_api.independence_blocked reviewer_id=%s subject_author_id=%s reason=metrics_unavailable guard_assertion_id=INV-SPS-REV-001 exc_type=%s",
            reviewer_id,
            subject_author_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "REVIEW_INDEPENDENCE_DENIED",
                "guard_assertion_id": "INV-SPS-REV-001",
                "normalized_business_invariants": get_normalized_business_invariants(
                    "INV-SPS-REV-001"
                ),
                "blocked_reason": "METRICS_UNAVAILABLE",
            },
        )

    status = _independence_status_for_rate(metrics.repeated_pair_rate)

    if status == ReviewerIndependenceStatus.WARNING:
        _emit_independence_log(
            "reviewer_api.independence_warning",
            reviewer_id=reviewer_id,
            subject_author_id=subject_author_id,
            metrics=metrics,
            status=status,
        )
    elif status == ReviewerIndependenceStatus.ESCALATION_REQUIRED:
        _emit_independence_log(
            "reviewer_api.independence_escalation",
            reviewer_id=reviewer_id,
            subject_author_id=subject_author_id,
            metrics=metrics,
            status=status,
        )
    elif status == ReviewerIndependenceStatus.BLOCKED:
        _emit_independence_log(
            "reviewer_api.independence_blocked",
            reviewer_id=reviewer_id,
            subject_author_id=subject_author_id,
            metrics=metrics,
            status=status,
            reason="threshold_exceeded",
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "REVIEW_INDEPENDENCE_DENIED",
                "guard_assertion_id": "INV-SPS-REV-001",
                "normalized_business_invariants": get_normalized_business_invariants(
                    "INV-SPS-REV-001"
                ),
                "blocked_reason": "INDEPENDENCE_THRESHOLD_BLOCKED",
            },
        )

    return status


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
    from sps.workflows.temporal import (
        connect_client,
    )  # local import to avoid import-time side effects

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

    now = _utcnow()

    # Independence guard — must precede any DB operation
    independence_status = _check_reviewer_independence(
        db,
        req.reviewer_id,
        req.subject_author_id,
        now,
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
    row = ReviewDecision(
        decision_id=req.decision_id,
        schema_version="1.0",
        case_id=req.case_id,
        object_type="permit_case",
        object_id=req.case_id,
        decision_outcome=req.outcome.value,
        reviewer_id=req.reviewer_id,
        subject_author_id=req.subject_author_id,
        reviewer_independence_status=independence_status.value,
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

    emit_audit_event(
        db,
        action="review_decision.created",
        actor_type="reviewer",
        actor_id=req.reviewer_id,
        correlation_id=req.case_id,
        request_id=req.decision_id,
        payload={
            "decision_id": req.decision_id,
            "case_id": req.case_id,
            "decision_outcome": req.outcome.value,
            "idempotency_key": req.idempotency_key,
            "dissent_flag": row.dissent_flag,
            "reviewer_independence_status": independence_status.value,
        },
        occurred_at=now,
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


@router.get(
    "/queue",
)
def get_review_queue(
    limit: int = Query(default=_DEFAULT_QUEUE_LIMIT, ge=1),
    db: Session = Depends(get_db),
) -> ReviewerQueueResponse:
    """Return the pending reviewer queue ordered by oldest cases first."""
    bounded_limit = _clamp_queue_limit(limit)
    rows = (
        db.query(PermitCase, Project)
        .join(Project, Project.case_id == PermitCase.case_id)
        .filter(PermitCase.case_state == "REVIEW_PENDING")
        .order_by(PermitCase.created_at.asc(), PermitCase.case_id.asc())
        .limit(bounded_limit)
        .all()
    )
    cases = [_queue_row_to_response(case, project) for case, project in rows]
    logger.info("reviewer_api.queue_fetched count=%d", len(cases))
    return ReviewerQueueResponse(cases=cases)


@router.get(
    "/cases/{case_id}/evidence-summary",
)
def get_evidence_summary(case_id: str, db: Session = Depends(get_db)) -> EvidenceSummaryResponse:
    """Aggregate evidence IDs and artifact metadata for a case."""
    case = db.get(PermitCase, case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "case_id": case_id},
        )

    evidence_ids = _collect_evidence_ids(db, case_id)
    artifacts: list[EvidenceArtifact] = []
    if evidence_ids:
        artifacts = (
            db.query(EvidenceArtifact)
            .filter(EvidenceArtifact.artifact_id.in_(evidence_ids))
            .order_by(EvidenceArtifact.created_at.asc(), EvidenceArtifact.artifact_id.asc())
            .all()
        )

    decisions = (
        db.query(ReviewDecision)
        .filter(ReviewDecision.case_id == case_id)
        .order_by(ReviewDecision.decision_at.desc())
        .all()
    )

    logger.info(
        "reviewer_api.evidence_summary case_id=%s evidence_count=%d artifact_count=%d decision_count=%d",
        case_id,
        len(evidence_ids),
        len(artifacts),
        len(decisions),
    )

    return EvidenceSummaryResponse(
        case_id=case_id,
        evidence_ids=evidence_ids,
        artifacts=[_artifact_row_to_response(row) for row in artifacts],
        review_decisions=[_decision_row_to_summary(row) for row in decisions],
        evidence_count=len(evidence_ids),
        artifact_count=len(artifacts),
        review_decision_count=len(decisions),
    )
