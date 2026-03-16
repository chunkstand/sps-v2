from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy.exc import IntegrityError
from temporalio import activity

from sps.db.models import CaseTransitionLedger, ContradictionArtifact, PermitCase, ReviewDecision
from sps.db.session import get_sessionmaker
from sps.failpoints import FailpointFired, fail_once
from sps.guards.guard_assertions import get_normalized_business_invariants
from sps.workflows.permit_case.contracts import (
    AppliedStateTransitionResult,
    CaseState,
    DeniedStateTransitionResult,
    PersistReviewDecisionRequest,
    StateTransitionRequest,
    StateTransitionResult,
    parse_state_transition_result,
)

logger = logging.getLogger(__name__)


@activity.defn
def ensure_permit_case_exists(case_id: str) -> bool:
    """Ensure a minimal `permit_cases` row exists.

    This proves the determinism boundary: all DB I/O happens in an activity, not
    in workflow code.

    Returns:
        True if the row was created, False if it already existed.
    """

    info = activity.info()
    logger.info(
        "activity.start name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s",
        info.workflow_id,
        info.workflow_run_id,
        case_id,
    )

    SessionLocal = get_sessionmaker()
    created = False

    try:
        with SessionLocal() as session:
            existing = session.get(PermitCase, case_id)
            if existing is None:
                created = True
                session.add(
                    PermitCase(
                        case_id=case_id,
                        tenant_id="tenant-local",
                        project_id=f"project-{case_id}",
                        # Contract-valid seed: the workflow proof path starts at REVIEW_PENDING.
                        case_state=CaseState.REVIEW_PENDING.value,
                        review_state="PENDING",
                        submission_mode="AUTOMATED",
                        portal_support_level="FULLY_SUPPORTED",
                        current_package_id=None,
                        current_release_profile="default",
                        legal_hold=False,
                        closure_reason=None,
                    )
                )
                session.commit()

        logger.info(
            "activity.ok name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s created=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            created,
        )
        return created
    except Exception as exc:
        # Temporal will record the exception; this log line provides a grep-able correlation tuple.
        logger.exception(
            "activity.error name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s exc_type=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            type(exc).__name__,
        )
        raise


def _safe_temporal_ids() -> tuple[str | None, str | None]:
    """Best-effort activity correlation identifiers.

    This activity is sometimes called directly in DB-level integration tests where
    Temporal activity context is unavailable.
    """

    try:
        info = activity.info()
        return info.workflow_id, info.workflow_run_id
    except Exception:
        return None, None


_EVENT_CASE_STATE_CHANGED = "CASE_STATE_CHANGED"
_EVENT_APPROVAL_GATE_DENIED = "APPROVAL_GATE_DENIED"
_EVENT_CONTRADICTION_ADVANCE_DENIED = "CONTRADICTION_ADVANCE_DENIED"
_GUARD_ASSERTION_REVIEW_GATE = "INV-SPS-STATE-002"
_GUARD_ASSERTION_CONTRADICTION = "INV-SPS-CONTRA-001"
_ALLOWED_REVIEW_OUTCOMES = {"ACCEPT", "ACCEPT_WITH_DISSENT"}


def _deny(
    *,
    denied_at: dt.datetime,
    event_type: str,
    denial_reason: str,
    guard_assertion_id: str | None = None,
    normalized_business_invariants: list[str] | None = None,
) -> DeniedStateTransitionResult:
    return DeniedStateTransitionResult(
        event_type=event_type,
        denied_at=denied_at,
        denial_reason=denial_reason,
        guard_assertion_id=guard_assertion_id,
        normalized_business_invariants=normalized_business_invariants,
    )


@activity.defn
def apply_state_transition(request: StateTransitionRequest | dict) -> StateTransitionResult:
    """Authoritative Postgres-backed transition guard + state mutation.

    - Fail-closed: unknown transitions and missing preconditions return a structured denial.
    - Durable audit: both applied and denied attempts are persisted to case_transition_ledger.
    - Idempotent: request.request_id is treated as the ledger primary key.
    """

    req = StateTransitionRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    requested_at = req.requested_at
    if requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=dt.UTC)

    logger.info(
        "activity.start name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s",
        workflow_id,
        run_id,
        req.request_id,
        req.case_id,
        req.from_state,
        req.to_state,
    )

    SessionLocal = get_sessionmaker()

    # First attempt in a single transaction; on a rare INSERT race we re-load.
    try:
        with SessionLocal() as session:
            try:
                idempotent = False
                persisted_event_type: str | None = None

                with session.begin():
                    existing = session.get(CaseTransitionLedger, req.request_id)
                    if existing is not None:
                        idempotent = True
                        persisted_event_type = existing.event_type
                        if existing.payload is None:
                            result = _deny(
                                denied_at=requested_at,
                                event_type=existing.event_type,
                                denial_reason="LEDGER_PAYLOAD_MISSING",
                            )
                        else:
                            result = parse_state_transition_result(existing.payload)
                    else:
                        case = session.get(PermitCase, req.case_id, with_for_update=True)
                        if case is None:
                            # With the current schema, we cannot write an audit row without
                            # an existing PermitCase due to FK constraints.
                            raise LookupError(f"permit_cases row not found for case_id={req.case_id}")

                        if case.case_state != req.from_state.value:
                            result = _deny(
                                denied_at=requested_at,
                                event_type="STATE_TRANSITION_DENIED",
                                denial_reason="FROM_STATE_MISMATCH",
                            )
                        elif (
                            req.from_state == CaseState.REVIEW_PENDING
                            and req.to_state == CaseState.APPROVED_FOR_SUBMISSION
                        ):
                            # Guard: blocking open contradictions must be resolved before advancement (CTL-14A).
                            blocking_contradiction = (
                                session.query(ContradictionArtifact)
                                .filter(
                                    ContradictionArtifact.case_id == req.case_id,
                                    ContradictionArtifact.blocking_effect.is_(True),
                                    ContradictionArtifact.resolution_status == "OPEN",
                                )
                                .first()
                            )
                            if blocking_contradiction is not None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_CONTRADICTION_ADVANCE_DENIED,
                                    denial_reason="BLOCKING_CONTRADICTION_UNRESOLVED",
                                    guard_assertion_id=_GUARD_ASSERTION_CONTRADICTION,
                                    normalized_business_invariants=get_normalized_business_invariants(
                                        _GUARD_ASSERTION_CONTRADICTION
                                    ),
                                )
                            else:
                                # Canonical protected transition: requires a valid ReviewDecision.
                                invariants = get_normalized_business_invariants(_GUARD_ASSERTION_REVIEW_GATE)

                                review_id = req.required_review_id
                                review: ReviewDecision | None = (
                                    session.get(ReviewDecision, review_id) if review_id else None
                                )

                                if (
                                    review_id is None
                                    or review is None
                                    or review.case_id != req.case_id
                                    or review.decision_outcome not in _ALLOWED_REVIEW_OUTCOMES
                                ):
                                    result = _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_APPROVAL_GATE_DENIED,
                                        denial_reason="REVIEW_DECISION_REQUIRED",
                                        guard_assertion_id=_GUARD_ASSERTION_REVIEW_GATE,
                                        normalized_business_invariants=invariants,
                                    )
                                else:
                                    result = AppliedStateTransitionResult(
                                        event_type=_EVENT_CASE_STATE_CHANGED,
                                        applied_at=requested_at,
                                    )
                                    case.case_state = req.to_state.value
                        else:
                            result = _deny(
                                denied_at=requested_at,
                                event_type="STATE_TRANSITION_DENIED",
                                denial_reason="UNKNOWN_TRANSITION",
                            )

                        session.add(
                            CaseTransitionLedger(
                                transition_id=req.request_id,
                                case_id=req.case_id,
                                event_type=result.event_type,
                                from_state=req.from_state.value,
                                to_state=req.to_state.value,
                                actor_type=req.actor_type.value,
                                actor_id=req.actor_id,
                                correlation_id=req.correlation_id,
                                occurred_at=requested_at,
                                payload=result.model_dump(mode="json"),
                            )
                        )
                        persisted_event_type = result.event_type

                failpoint_key = f"apply_state_transition.after_commit/{req.request_id}"
                try:
                    fail_once(failpoint_key)
                except FailpointFired:
                    logger.error(
                        "activity.failpoint name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s correlation_id=%s failpoint_key=%s",
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        req.correlation_id,
                        failpoint_key,
                    )
                    raise

                if idempotent:
                    logger.info(
                        "activity.ok name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s event_type=%s result=%s idempotent=1",
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        persisted_event_type,
                        result.result,
                    )
                else:
                    log_event = "activity.ok" if result.result == "applied" else "activity.denied"
                    logger.info(
                        "%s name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s event_type=%s result=%s idempotent=0",
                        log_event,
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        req.from_state,
                        req.to_state,
                        result.event_type,
                        result.result,
                    )

                return result
            except IntegrityError:
                # If we raced another attempt with the same request_id, the primary key
                # ensures we can safely re-load and return the persisted outcome.
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(CaseTransitionLedger, req.request_id)
            if existing is None:
                raise RuntimeError(f"ledger insert failed but row not found for request_id={req.request_id}")
            if existing.payload is None:
                result = _deny(
                    denied_at=requested_at,
                    event_type=existing.event_type,
                    denial_reason="LEDGER_PAYLOAD_MISSING",
                )
            else:
                result = parse_state_transition_result(existing.payload)

            logger.info(
                "activity.ok name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s event_type=%s result=%s idempotent=1",
                workflow_id,
                run_id,
                req.request_id,
                req.case_id,
                existing.event_type,
                result.result,
            )
            return result
    except Exception as exc:
        logger.exception(
            "activity.error name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s exc_type=%s",
            workflow_id,
            run_id,
            req.request_id,
            req.case_id,
            req.from_state,
            req.to_state,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_review_decision(request: PersistReviewDecisionRequest | dict) -> str:
    """Persist a ReviewDecision row idempotently.

    Idempotency boundary: review_decisions.idempotency_key (unique).

    Returns:
        The persisted decision_id.
    """

    req = PersistReviewDecisionRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    decision_at = req.decision_at
    if decision_at.tzinfo is None:
        decision_at = decision_at.replace(tzinfo=dt.UTC)

    logger.info(
        "activity.start name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotency_key=%s outcome=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.decision_id,
        req.idempotency_key,
        req.decision_outcome,
    )

    SessionLocal = get_sessionmaker()

    try:
        with SessionLocal() as session:
            try:
                idempotent = False
                persisted_decision_id: str | None = None

                with session.begin():
                    existing = (
                        session.query(ReviewDecision)
                        .filter(ReviewDecision.idempotency_key == req.idempotency_key)
                        .one_or_none()
                    )
                    if existing is not None:
                        idempotent = True
                        persisted_decision_id = existing.decision_id
                    else:
                        session.add(
                            ReviewDecision(
                                decision_id=req.decision_id,
                                schema_version=req.schema_version,
                                case_id=req.case_id,
                                object_type=req.object_type,
                                object_id=req.object_id,
                                decision_outcome=req.decision_outcome.value,
                                reviewer_id=req.reviewer_id,
                                reviewer_independence_status=req.reviewer_independence_status.value,
                                evidence_ids=req.evidence_ids,
                                contradiction_resolution=req.contradiction_resolution,
                                dissent_flag=req.dissent_flag,
                                notes=req.notes,
                                decision_at=decision_at,
                                idempotency_key=req.idempotency_key,
                            )
                        )
                        persisted_decision_id = req.decision_id

                assert persisted_decision_id is not None

                failpoint_key = f"persist_review_decision.after_commit/{req.idempotency_key}"
                try:
                    fail_once(failpoint_key)
                except FailpointFired:
                    logger.error(
                        "activity.failpoint name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotency_key=%s failpoint_key=%s",
                        workflow_id,
                        run_id,
                        req.case_id,
                        persisted_decision_id,
                        req.idempotency_key,
                        failpoint_key,
                    )
                    raise

                logger.info(
                    "activity.ok name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    persisted_decision_id,
                    1 if idempotent else 0,
                )
                return persisted_decision_id
            except IntegrityError:
                session.rollback()
                raced = (
                    session.query(ReviewDecision)
                    .filter(ReviewDecision.idempotency_key == req.idempotency_key)
                    .one_or_none()
                )
                if raced is None:
                    raise RuntimeError(
                        "review_decisions insert raced but row not found for idempotency_key="
                        f"{req.idempotency_key}"
                    )

                logger.info(
                    "activity.ok name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotent=1",
                    workflow_id,
                    run_id,
                    req.case_id,
                    raced.decision_id,
                )
                return raced.decision_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.decision_id,
            type(exc).__name__,
        )
        raise
