from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

from sps.workflows.permit_case.contracts import PermitCaseWorkflowInput
from sps.workflows.permit_case.contracts import ReviewDecisionSignal

with workflow.unsafe.imports_passed_through():
    # Activity modules typically import non-deterministic libraries (DB drivers, network clients).
    # Import them via pass-through so workflow sandboxing doesn't attempt to re-execute their
    # import-time side effects.
    from sps.workflows.permit_case.activities import ensure_permit_case_exists


@workflow.defn
class PermitCaseWorkflow:
    """Minimal deterministic workflow.

    Contract:
      1) bootstrap the case record via a Postgres-backed activity
      2) wait (deterministically) for a ReviewDecision signal

    The workflow itself performs no I/O.
    """

    def __init__(self) -> None:
        self._case_id: str | None = None
        self._review_decision: ReviewDecisionSignal | None = None

    @workflow.run
    async def run(self, input: PermitCaseWorkflowInput) -> ReviewDecisionSignal:
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

        workflow.logger.info(
            "workflow.waiting name=PermitCaseWorkflow workflow_id=%s run_id=%s case_id=%s signal=ReviewDecision",
            info.workflow_id,
            info.run_id,
            self._case_id,
        )

        await workflow.wait_condition(lambda: self._review_decision is not None)

        assert self._review_decision is not None  # for type-checkers
        workflow.logger.info(
            "workflow.complete name=PermitCaseWorkflow workflow_id=%s run_id=%s case_id=%s decision_outcome=%s reviewer_id=%s",
            info.workflow_id,
            info.run_id,
            self._case_id,
            self._review_decision.decision_outcome,
            self._review_decision.reviewer_id,
        )
        return self._review_decision

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
