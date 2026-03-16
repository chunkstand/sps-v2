from __future__ import annotations

from datetime import timedelta
import datetime as dt

from temporalio import workflow

from sps.workflows.permit_case.contracts import (
    ActorType,
    CaseState,
    PermitCaseWorkflowInput,
    PermitCaseWorkflowResult,
    ReviewDecisionSignal,
    StateTransitionRequest,
    parse_state_transition_result,
)

with workflow.unsafe.imports_passed_through():
    # Activity modules typically import non-deterministic libraries (DB drivers, network clients).
    # Import them via pass-through so workflow sandboxing doesn't attempt to re-execute their
    # import-time side effects.
    from sps.workflows.permit_case.activities import (
        apply_state_transition,
        ensure_permit_case_exists,
    )


def _utc(dt_value: dt.datetime) -> dt.datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=dt.UTC)
    return dt_value


def _transition_request_id(*, workflow_id: str, run_id: str, transition: str, attempt: int) -> str:
    # Deterministic and grep-able. Postgres transition_id is TEXT so length is acceptable.
    return f"{workflow_id}/{run_id}/{transition}/attempt-{attempt}"


@workflow.defn
class PermitCaseWorkflow:
    """Guarded transition proof workflow.

    Contract:
      1) bootstrap the case record via a Postgres-backed activity
      2) attempt protected transition REVIEW_PENDING → APPROVED_FOR_SUBMISSION
      3) on APPROVAL_GATE_DENIED, wait deterministically for ReviewDecision signal
      4) use signal.decision_id (persisted by the reviewer API) as required_review_id,
         re-attempt the guarded transition
    """

    def __init__(self) -> None:
        self._case_id: str | None = None
        self._review_decision: ReviewDecisionSignal | None = None

    @workflow.run
    async def run(self, input: PermitCaseWorkflowInput) -> PermitCaseWorkflowResult:
        self._case_id = input.case_id
        info = workflow.info()

        workflow.logger.info(
            "workflow.start name=PermitCaseWorkflow workflow_id=%s run_id=%s case_id=%s",
            info.workflow_id,
            info.run_id,
            self._case_id,
        )

        await workflow.execute_activity(
            ensure_permit_case_exists,
            self._case_id,
            start_to_close_timeout=timedelta(seconds=30),
        )

        correlation_id = f"{info.workflow_id}:{info.run_id}"
        transition_name = "review_pending_to_approved_for_submission"

        request_id_1 = _transition_request_id(
            workflow_id=info.workflow_id,
            run_id=info.run_id,
            transition=transition_name,
            attempt=1,
        )
        request_id_2 = _transition_request_id(
            workflow_id=info.workflow_id,
            run_id=info.run_id,
            transition=transition_name,
            attempt=2,
        )

        requested_at_1 = _utc(workflow.now())
        workflow.logger.info(
            "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
            info.workflow_id,
            info.run_id,
            self._case_id,
            request_id_1,
            CaseState.REVIEW_PENDING,
            CaseState.APPROVED_FOR_SUBMISSION,
        )

        raw_initial = await workflow.execute_activity(
            apply_state_transition,
            StateTransitionRequest(
                request_id=request_id_1,
                case_id=self._case_id,
                from_state=CaseState.REVIEW_PENDING,
                to_state=CaseState.APPROVED_FOR_SUBMISSION,
                actor_type=ActorType.system_guard,
                actor_id="system-guard",
                correlation_id=correlation_id,
                causation_id=None,
                required_review_id=None,
                required_evidence_ids=[],
                override_id=None,
                requested_at=requested_at_1,
                notes=None,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )
        initial_result = parse_state_transition_result(
            raw_initial.model_dump() if hasattr(raw_initial, "model_dump") else raw_initial
        )

        if initial_result.result == "applied":
            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                request_id_1,
                initial_result.event_type,
            )
            return PermitCaseWorkflowResult(
                case_id=self._case_id,
                correlation_id=correlation_id,
                initial_request_id=request_id_1,
                initial_result=initial_result,
                review_decision_id=None,
                review_signal=None,
                final_request_id=request_id_1,
                final_result=initial_result,
            )

        workflow.logger.info(
            "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s guard_assertion_id=%s",
            info.workflow_id,
            info.run_id,
            self._case_id,
            request_id_1,
            initial_result.event_type,
            getattr(initial_result, "denial_reason", None),
            getattr(initial_result, "guard_assertion_id", None),
        )

        if initial_result.event_type != "APPROVAL_GATE_DENIED":
            raise RuntimeError(
                f"unexpected denial for guarded transition (event_type={initial_result.event_type})"
            )

        workflow.logger.info(
            "workflow.waiting_for_review workflow_id=%s run_id=%s case_id=%s signal=ReviewDecision",
            info.workflow_id,
            info.run_id,
            self._case_id,
        )
        await workflow.wait_condition(lambda: self._review_decision is not None)

        assert self._review_decision is not None  # for type-checkers
        # Defensive: if a client sent a plain dict (or the converter didn't hydrate the
        # Pydantic model), normalize it before use.
        review_signal = ReviewDecisionSignal.model_validate(self._review_decision)
        self._review_decision = review_signal

        workflow.logger.info(
            "workflow.review_received workflow_id=%s run_id=%s case_id=%s decision_outcome=%s reviewer_id=%s",
            info.workflow_id,
            info.run_id,
            self._case_id,
            review_signal.decision_outcome,
            review_signal.reviewer_id,
        )

        # M003/S01: persist_review_decision activity removed. The reviewer API is now
        # the sole writer of the review_decisions table. The signal carries the
        # already-persisted decision_id; raise loudly if it's missing (legacy signal).
        if review_signal.decision_id is None:
            raise RuntimeError(
                "ReviewDecisionSignal missing decision_id — legacy signal unsupported after M003/S01"
            )
        review_decision_id = review_signal.decision_id

        requested_at_2 = _utc(workflow.now())
        workflow.logger.info(
            "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=2 required_review_id=%s",
            info.workflow_id,
            info.run_id,
            self._case_id,
            request_id_2,
            CaseState.REVIEW_PENDING,
            CaseState.APPROVED_FOR_SUBMISSION,
            review_decision_id,
        )

        raw_final = await workflow.execute_activity(
            apply_state_transition,
            StateTransitionRequest(
                request_id=request_id_2,
                case_id=self._case_id,
                from_state=CaseState.REVIEW_PENDING,
                to_state=CaseState.APPROVED_FOR_SUBMISSION,
                actor_type=ActorType.system_guard,
                actor_id="system-guard",
                correlation_id=correlation_id,
                causation_id=request_id_1,
                required_review_id=review_decision_id,
                required_evidence_ids=[],
                override_id=None,
                requested_at=requested_at_2,
                notes=None,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )
        final_result = parse_state_transition_result(
            raw_final.model_dump() if hasattr(raw_final, "model_dump") else raw_final
        )

        if final_result.result != "applied":
            workflow.logger.info(
                "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                request_id_2,
                final_result.event_type,
                getattr(final_result, "denial_reason", None),
            )
            raise RuntimeError(
                f"guarded transition did not apply after review (event_type={final_result.event_type})"
            )

        workflow.logger.info(
            "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
            info.workflow_id,
            info.run_id,
            self._case_id,
            request_id_2,
            final_result.event_type,
        )

        return PermitCaseWorkflowResult(
            case_id=self._case_id,
            correlation_id=correlation_id,
            initial_request_id=request_id_1,
            initial_result=initial_result,
            review_decision_id=review_decision_id,
            review_signal=review_signal,
            final_request_id=request_id_2,
            final_result=final_result,
        )

    @workflow.signal(name="ReviewDecision")
    async def review_decision(self, signal: ReviewDecisionSignal) -> None:
        # Idempotent-ish: ignore duplicate signals if we already have a decision.
        if self._review_decision is None:
            self._review_decision = signal

        info = workflow.info()
        workflow.logger.info(
            "workflow.signal name=PermitCaseWorkflow workflow_id=%s run_id=%s case_id=%s signal=ReviewDecision",
            info.workflow_id,
            info.run_id,
            self._case_id,
        )
