from __future__ import annotations

from datetime import timedelta
import datetime as dt

from temporalio import workflow

from sps.workflows.permit_case.contracts import (
    ActorType,
    CaseState,
    PermitCaseStateSnapshot,
    PermitCaseWorkflowInput,
    PermitCaseWorkflowResult,
    PersistComplianceEvaluationRequest,
    PersistIncentiveAssessmentRequest,
    PersistJurisdictionResolutionRequest,
    PersistRequirementSetRequest,
    PersistSubmissionPackageRequest,
    ReviewDecisionSignal,
    SubmissionAdapterOutcome,
    SubmissionAdapterRequest,
    SubmissionAdapterResult,
    StateTransitionRequest,
    parse_state_transition_result,
    submission_attempt_id_for_workflow,
    submission_attempt_idempotency_key,
)

with workflow.unsafe.imports_passed_through():
    # Activity modules typically import non-deterministic libraries (DB drivers, network clients).
    # Import them via pass-through so workflow sandboxing doesn't attempt to re-execute their
    # import-time side effects.
    from sps.workflows.permit_case.activities import (
        apply_state_transition,
        deterministic_submission_adapter,
        ensure_permit_case_exists,
        fetch_permit_case_state,
        persist_compliance_evaluation,
        persist_incentive_assessment,
        persist_jurisdiction_resolutions,
        persist_requirement_sets,
        persist_submission_package,
    )


def _utc(dt_value: dt.datetime) -> dt.datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=dt.UTC)
    return dt_value


def _transition_request_id(*, workflow_id: str, run_id: str, transition: str, attempt: int) -> str:
    # Deterministic and grep-able. Postgres transition_id is TEXT so length is acceptable.
    return f"{workflow_id}/{run_id}/{transition}/attempt-{attempt}"


def _activity_request_id(*, workflow_id: str, run_id: str, activity_name: str, attempt: int) -> str:
    return f"{workflow_id}/{run_id}/{activity_name}/attempt-{attempt}"


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

        raw_snapshot = await workflow.execute_activity(
            fetch_permit_case_state,
            self._case_id,
            start_to_close_timeout=timedelta(seconds=30),
        )
        if isinstance(raw_snapshot, PermitCaseStateSnapshot):
            snapshot = raw_snapshot
        elif hasattr(raw_snapshot, "model_dump"):
            snapshot = PermitCaseStateSnapshot.model_validate(raw_snapshot.model_dump())
        else:
            snapshot = PermitCaseStateSnapshot.model_validate(raw_snapshot)

        async def _run_submission_step(
            *,
            package_id: str,
            initial_request_id: str | None,
            initial_result,
        ) -> PermitCaseWorkflowResult:
            submission_attempt_id = submission_attempt_id_for_workflow(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                attempt=1,
            )
            submission_request_id = _activity_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                activity_name="submission_adapter",
                attempt=1,
            )
            adapter_request = SubmissionAdapterRequest(
                request_id=submission_request_id,
                submission_attempt_id=submission_attempt_id,
                case_id=self._case_id,
                package_id=package_id,
                manifest_id="MANIFEST-UNKNOWN",
                target_portal_family="CITY_PORTAL_FAMILY_A",
                artifact_digests={},
                idempotency_key=submission_attempt_idempotency_key(
                    case_id=self._case_id,
                    attempt=1,
                ),
                attempt_number=1,
                correlation_id=correlation_id,
            )
            raw_adapter = await workflow.execute_activity(
                deterministic_submission_adapter,
                adapter_request,
                start_to_close_timeout=timedelta(seconds=60),
            )
            adapter_result = (
                raw_adapter
                if isinstance(raw_adapter, SubmissionAdapterResult)
                else SubmissionAdapterResult.model_validate(raw_adapter)
            )

            workflow.logger.info(
                "workflow.submission_adapter_result workflow_id=%s run_id=%s case_id=%s attempt_id=%s outcome=%s receipt_artifact_id=%s manual_fallback_id=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                adapter_result.submission_attempt_id,
                adapter_result.outcome,
                adapter_result.receipt_artifact_id,
                adapter_result.manual_fallback_package_id,
            )

            if adapter_result.outcome == SubmissionAdapterOutcome.UNSUPPORTED_WORKFLOW:
                transition_name = "document_complete_to_manual_submission_required"
                target_state = CaseState.MANUAL_SUBMISSION_REQUIRED
            elif adapter_result.outcome == SubmissionAdapterOutcome.SUCCESS:
                transition_name = "document_complete_to_submitted"
                target_state = CaseState.SUBMITTED
            else:
                raise RuntimeError(
                    "submission adapter failed "
                    f"(attempt_id={adapter_result.submission_attempt_id}, outcome={adapter_result.outcome})"
                )

            submission_transition_id = _transition_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                transition=transition_name,
                attempt=1,
            )
            submission_requested_at = _utc(workflow.now())
            workflow.logger.info(
                "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
                info.workflow_id,
                info.run_id,
                self._case_id,
                submission_transition_id,
                CaseState.DOCUMENT_COMPLETE,
                target_state,
            )

            raw_submission_transition = await workflow.execute_activity(
                apply_state_transition,
                StateTransitionRequest(
                    request_id=submission_transition_id,
                    case_id=self._case_id,
                    from_state=CaseState.DOCUMENT_COMPLETE,
                    to_state=target_state,
                    actor_type=ActorType.system_guard,
                    actor_id="system-guard",
                    correlation_id=correlation_id,
                    causation_id=initial_request_id,
                    required_review_id=None,
                    required_evidence_ids=[],
                    override_id=None,
                    requested_at=submission_requested_at,
                    notes=None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            submission_result = parse_state_transition_result(
                raw_submission_transition.model_dump()
                if hasattr(raw_submission_transition, "model_dump")
                else raw_submission_transition
            )

            if submission_result.result != "applied":
                workflow.logger.info(
                    "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s",
                    info.workflow_id,
                    info.run_id,
                    self._case_id,
                    submission_transition_id,
                    submission_result.event_type,
                    getattr(submission_result, "denial_reason", None),
                )
                raise RuntimeError(
                    "submission transition did not apply "
                    f"(event_type={submission_result.event_type})"
                )

            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                submission_transition_id,
                submission_result.event_type,
            )

            resolved_initial_request_id = initial_request_id or submission_transition_id
            resolved_initial_result = initial_result or submission_result

            return PermitCaseWorkflowResult(
                case_id=self._case_id,
                correlation_id=correlation_id,
                initial_request_id=resolved_initial_request_id,
                initial_result=resolved_initial_result,
                review_decision_id=None,
                review_signal=None,
                final_request_id=submission_transition_id,
                final_result=submission_result,
                intake_request_id=None,
                intake_result=None,
            )

        if snapshot.case_state == CaseState.INTAKE_PENDING:
            transition_name = "intake_pending_to_intake_complete"
            request_id = _transition_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                transition=transition_name,
                attempt=1,
            )
            requested_at = _utc(workflow.now())
            workflow.logger.info(
                "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
                info.workflow_id,
                info.run_id,
                self._case_id,
                request_id,
                CaseState.INTAKE_PENDING,
                CaseState.INTAKE_COMPLETE,
            )

            raw_intake = await workflow.execute_activity(
                apply_state_transition,
                StateTransitionRequest(
                    request_id=request_id,
                    case_id=self._case_id,
                    from_state=CaseState.INTAKE_PENDING,
                    to_state=CaseState.INTAKE_COMPLETE,
                    actor_type=ActorType.system_guard,
                    actor_id="system-guard",
                    correlation_id=correlation_id,
                    causation_id=None,
                    required_review_id=None,
                    required_evidence_ids=[],
                    override_id=None,
                    requested_at=requested_at,
                    notes=None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            intake_result = parse_state_transition_result(
                raw_intake.model_dump() if hasattr(raw_intake, "model_dump") else raw_intake
            )

            if intake_result.result != "applied":
                workflow.logger.info(
                    "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s",
                    info.workflow_id,
                    info.run_id,
                    self._case_id,
                    request_id,
                    intake_result.event_type,
                    getattr(intake_result, "denial_reason", None),
                )
                raise RuntimeError(
                    f"intake transition did not apply (event_type={intake_result.event_type})"
                )

            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                request_id,
                intake_result.event_type,
            )
            return PermitCaseWorkflowResult(
                case_id=self._case_id,
                correlation_id=correlation_id,
                initial_request_id=request_id,
                initial_result=intake_result,
                review_decision_id=None,
                review_signal=None,
                final_request_id=request_id,
                final_result=intake_result,
                intake_request_id=request_id,
                intake_result=intake_result,
            )

        if snapshot.case_state == CaseState.INTAKE_COMPLETE:
            jurisdiction_activity_id = _activity_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                activity_name="persist_jurisdiction",
                attempt=1,
            )
            await workflow.execute_activity(
                persist_jurisdiction_resolutions,
                PersistJurisdictionResolutionRequest(
                    request_id=jurisdiction_activity_id,
                    case_id=self._case_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            jurisdiction_transition = "intake_complete_to_jurisdiction_complete"
            jurisdiction_request_id = _transition_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                transition=jurisdiction_transition,
                attempt=1,
            )
            jurisdiction_requested_at = _utc(workflow.now())
            workflow.logger.info(
                "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
                info.workflow_id,
                info.run_id,
                self._case_id,
                jurisdiction_request_id,
                CaseState.INTAKE_COMPLETE,
                CaseState.JURISDICTION_COMPLETE,
            )

            raw_jurisdiction = await workflow.execute_activity(
                apply_state_transition,
                StateTransitionRequest(
                    request_id=jurisdiction_request_id,
                    case_id=self._case_id,
                    from_state=CaseState.INTAKE_COMPLETE,
                    to_state=CaseState.JURISDICTION_COMPLETE,
                    actor_type=ActorType.system_guard,
                    actor_id="system-guard",
                    correlation_id=correlation_id,
                    causation_id=None,
                    required_review_id=None,
                    required_evidence_ids=[],
                    override_id=None,
                    requested_at=jurisdiction_requested_at,
                    notes=None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            jurisdiction_result = parse_state_transition_result(
                raw_jurisdiction.model_dump() if hasattr(raw_jurisdiction, "model_dump") else raw_jurisdiction
            )

            if jurisdiction_result.result != "applied":
                workflow.logger.info(
                    "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s",
                    info.workflow_id,
                    info.run_id,
                    self._case_id,
                    jurisdiction_request_id,
                    jurisdiction_result.event_type,
                    getattr(jurisdiction_result, "denial_reason", None),
                )
                raise RuntimeError(
                    "jurisdiction transition did not apply "
                    f"(event_type={jurisdiction_result.event_type})"
                )

            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                jurisdiction_request_id,
                jurisdiction_result.event_type,
            )

            requirements_activity_id = _activity_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                activity_name="persist_requirements",
                attempt=1,
            )
            await workflow.execute_activity(
                persist_requirement_sets,
                PersistRequirementSetRequest(
                    request_id=requirements_activity_id,
                    case_id=self._case_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            requirements_transition = "jurisdiction_complete_to_research_complete"
            requirements_request_id = _transition_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                transition=requirements_transition,
                attempt=1,
            )
            requirements_requested_at = _utc(workflow.now())
            workflow.logger.info(
                "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
                info.workflow_id,
                info.run_id,
                self._case_id,
                requirements_request_id,
                CaseState.JURISDICTION_COMPLETE,
                CaseState.RESEARCH_COMPLETE,
            )

            raw_requirements = await workflow.execute_activity(
                apply_state_transition,
                StateTransitionRequest(
                    request_id=requirements_request_id,
                    case_id=self._case_id,
                    from_state=CaseState.JURISDICTION_COMPLETE,
                    to_state=CaseState.RESEARCH_COMPLETE,
                    actor_type=ActorType.system_guard,
                    actor_id="system-guard",
                    correlation_id=correlation_id,
                    causation_id=jurisdiction_request_id,
                    required_review_id=None,
                    required_evidence_ids=[],
                    override_id=None,
                    requested_at=requirements_requested_at,
                    notes=None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            requirements_result = parse_state_transition_result(
                raw_requirements.model_dump() if hasattr(raw_requirements, "model_dump") else raw_requirements
            )

            if requirements_result.result != "applied":
                workflow.logger.info(
                    "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s",
                    info.workflow_id,
                    info.run_id,
                    self._case_id,
                    requirements_request_id,
                    requirements_result.event_type,
                    getattr(requirements_result, "denial_reason", None),
                )
                raise RuntimeError(
                    "requirements transition did not apply "
                    f"(event_type={requirements_result.event_type})"
                )

            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                requirements_request_id,
                requirements_result.event_type,
            )

            compliance_activity_id = _activity_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                activity_name="persist_compliance",
                attempt=1,
            )
            await workflow.execute_activity(
                persist_compliance_evaluation,
                PersistComplianceEvaluationRequest(
                    request_id=compliance_activity_id,
                    case_id=self._case_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            compliance_transition = "research_complete_to_compliance_complete"
            compliance_request_id = _transition_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                transition=compliance_transition,
                attempt=1,
            )
            compliance_requested_at = _utc(workflow.now())
            workflow.logger.info(
                "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
                info.workflow_id,
                info.run_id,
                self._case_id,
                compliance_request_id,
                CaseState.RESEARCH_COMPLETE,
                CaseState.COMPLIANCE_COMPLETE,
            )

            raw_compliance = await workflow.execute_activity(
                apply_state_transition,
                StateTransitionRequest(
                    request_id=compliance_request_id,
                    case_id=self._case_id,
                    from_state=CaseState.RESEARCH_COMPLETE,
                    to_state=CaseState.COMPLIANCE_COMPLETE,
                    actor_type=ActorType.system_guard,
                    actor_id="system-guard",
                    correlation_id=correlation_id,
                    causation_id=requirements_request_id,
                    required_review_id=None,
                    required_evidence_ids=[],
                    override_id=None,
                    requested_at=compliance_requested_at,
                    notes=None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            compliance_result = parse_state_transition_result(
                raw_compliance.model_dump() if hasattr(raw_compliance, "model_dump") else raw_compliance
            )

            if compliance_result.result != "applied":
                workflow.logger.info(
                    "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s guard_assertion_id=%s",
                    info.workflow_id,
                    info.run_id,
                    self._case_id,
                    compliance_request_id,
                    compliance_result.event_type,
                    getattr(compliance_result, "denial_reason", None),
                    getattr(compliance_result, "guard_assertion_id", None),
                )
                raise RuntimeError(
                    "compliance transition did not apply "
                    f"(event_type={compliance_result.event_type})"
                )

            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                compliance_request_id,
                compliance_result.event_type,
            )

            incentives_activity_id = _activity_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                activity_name="persist_incentives",
                attempt=1,
            )
            await workflow.execute_activity(
                persist_incentive_assessment,
                PersistIncentiveAssessmentRequest(
                    request_id=incentives_activity_id,
                    case_id=self._case_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            incentives_transition = "compliance_complete_to_incentives_complete"
            incentives_request_id = _transition_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                transition=incentives_transition,
                attempt=1,
            )
            incentives_requested_at = _utc(workflow.now())
            workflow.logger.info(
                "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
                info.workflow_id,
                info.run_id,
                self._case_id,
                incentives_request_id,
                CaseState.COMPLIANCE_COMPLETE,
                CaseState.INCENTIVES_COMPLETE,
            )

            raw_incentives = await workflow.execute_activity(
                apply_state_transition,
                StateTransitionRequest(
                    request_id=incentives_request_id,
                    case_id=self._case_id,
                    from_state=CaseState.COMPLIANCE_COMPLETE,
                    to_state=CaseState.INCENTIVES_COMPLETE,
                    actor_type=ActorType.system_guard,
                    actor_id="system-guard",
                    correlation_id=correlation_id,
                    causation_id=compliance_request_id,
                    required_review_id=None,
                    required_evidence_ids=[],
                    override_id=None,
                    requested_at=incentives_requested_at,
                    notes=None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            incentives_result = parse_state_transition_result(
                raw_incentives.model_dump() if hasattr(raw_incentives, "model_dump") else raw_incentives
            )

            if incentives_result.result != "applied":
                workflow.logger.info(
                    "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s guard_assertion_id=%s",
                    info.workflow_id,
                    info.run_id,
                    self._case_id,
                    incentives_request_id,
                    incentives_result.event_type,
                    getattr(incentives_result, "denial_reason", None),
                    getattr(incentives_result, "guard_assertion_id", None),
                )
                raise RuntimeError(
                    "incentives transition did not apply "
                    f"(event_type={incentives_result.event_type})"
                )

            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                incentives_request_id,
                incentives_result.event_type,
            )

            return PermitCaseWorkflowResult(
                case_id=self._case_id,
                correlation_id=correlation_id,
                initial_request_id=jurisdiction_request_id,
                initial_result=jurisdiction_result,
                review_decision_id=None,
                review_signal=None,
                final_request_id=incentives_request_id,
                final_result=incentives_result,
                intake_request_id=None,
                intake_result=None,
            )

        if snapshot.case_state == CaseState.COMPLIANCE_COMPLETE:
            incentives_activity_id = _activity_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                activity_name="persist_incentives",
                attempt=1,
            )
            await workflow.execute_activity(
                persist_incentive_assessment,
                PersistIncentiveAssessmentRequest(
                    request_id=incentives_activity_id,
                    case_id=self._case_id,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            incentives_transition = "compliance_complete_to_incentives_complete"
            incentives_request_id = _transition_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                transition=incentives_transition,
                attempt=1,
            )
            incentives_requested_at = _utc(workflow.now())
            workflow.logger.info(
                "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
                info.workflow_id,
                info.run_id,
                self._case_id,
                incentives_request_id,
                CaseState.COMPLIANCE_COMPLETE,
                CaseState.INCENTIVES_COMPLETE,
            )

            raw_incentives = await workflow.execute_activity(
                apply_state_transition,
                StateTransitionRequest(
                    request_id=incentives_request_id,
                    case_id=self._case_id,
                    from_state=CaseState.COMPLIANCE_COMPLETE,
                    to_state=CaseState.INCENTIVES_COMPLETE,
                    actor_type=ActorType.system_guard,
                    actor_id="system-guard",
                    correlation_id=correlation_id,
                    causation_id=None,
                    required_review_id=None,
                    required_evidence_ids=[],
                    override_id=None,
                    requested_at=incentives_requested_at,
                    notes=None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            incentives_result = parse_state_transition_result(
                raw_incentives.model_dump() if hasattr(raw_incentives, "model_dump") else raw_incentives
            )

            if incentives_result.result != "applied":
                workflow.logger.info(
                    "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s guard_assertion_id=%s",
                    info.workflow_id,
                    info.run_id,
                    self._case_id,
                    incentives_request_id,
                    incentives_result.event_type,
                    getattr(incentives_result, "denial_reason", None),
                    getattr(incentives_result, "guard_assertion_id", None),
                )
                raise RuntimeError(
                    "incentives transition did not apply "
                    f"(event_type={incentives_result.event_type})"
                )

            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                incentives_request_id,
                incentives_result.event_type,
            )

            return PermitCaseWorkflowResult(
                case_id=self._case_id,
                correlation_id=correlation_id,
                initial_request_id=incentives_request_id,
                initial_result=incentives_result,
                review_decision_id=None,
                review_signal=None,
                final_request_id=incentives_request_id,
                final_result=incentives_result,
                intake_request_id=None,
                intake_result=None,
            )
        
        if snapshot.case_state == CaseState.INCENTIVES_COMPLETE:
            # Generate and persist submission package
            package_activity_id = _activity_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                activity_name="persist_submission_package",
                attempt=1,
            )
            package_id = await workflow.execute_activity(
                persist_submission_package,
                PersistSubmissionPackageRequest(
                    request_id=package_activity_id,
                    case_id=self._case_id,
                ),
                start_to_close_timeout=timedelta(seconds=60),
            )
            
            workflow.logger.info(
                "workflow.package_persisted workflow_id=%s run_id=%s case_id=%s package_id=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                package_id,
            )
            
            # Transition INCENTIVES_COMPLETE → DOCUMENT_COMPLETE
            document_transition = "incentives_complete_to_document_complete"
            document_request_id = _transition_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                transition=document_transition,
                attempt=1,
            )
            document_requested_at = _utc(workflow.now())
            workflow.logger.info(
                "workflow.transition_attempt workflow_id=%s run_id=%s case_id=%s request_id=%s from_state=%s to_state=%s attempt=1",
                info.workflow_id,
                info.run_id,
                self._case_id,
                document_request_id,
                CaseState.INCENTIVES_COMPLETE,
                CaseState.DOCUMENT_COMPLETE,
            )
            
            raw_document = await workflow.execute_activity(
                apply_state_transition,
                StateTransitionRequest(
                    request_id=document_request_id,
                    case_id=self._case_id,
                    from_state=CaseState.INCENTIVES_COMPLETE,
                    to_state=CaseState.DOCUMENT_COMPLETE,
                    actor_type=ActorType.system_guard,
                    actor_id="system-guard",
                    correlation_id=correlation_id,
                    causation_id=None,
                    required_review_id=None,
                    required_evidence_ids=[],
                    override_id=None,
                    requested_at=document_requested_at,
                    notes=None,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            document_result = parse_state_transition_result(
                raw_document.model_dump() if hasattr(raw_document, "model_dump") else raw_document
            )
            
            if document_result.result != "applied":
                workflow.logger.info(
                    "workflow.transition_denied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s denial_reason=%s",
                    info.workflow_id,
                    info.run_id,
                    self._case_id,
                    document_request_id,
                    document_result.event_type,
                    getattr(document_result, "denial_reason", None),
                )
                raise RuntimeError(
                    "document transition did not apply "
                    f"(event_type={document_result.event_type})"
                )
            
            workflow.logger.info(
                "workflow.transition_applied workflow_id=%s run_id=%s case_id=%s request_id=%s event_type=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                document_request_id,
                document_result.event_type,
            )
            
            return await _run_submission_step(
                package_id=package_id,
                initial_request_id=document_request_id,
                initial_result=document_result,
            )

        if snapshot.case_state == CaseState.DOCUMENT_COMPLETE:
            package_activity_id = _activity_request_id(
                workflow_id=info.workflow_id,
                run_id=info.run_id,
                activity_name="persist_submission_package",
                attempt=1,
            )
            package_id = await workflow.execute_activity(
                persist_submission_package,
                PersistSubmissionPackageRequest(
                    request_id=package_activity_id,
                    case_id=self._case_id,
                ),
                start_to_close_timeout=timedelta(seconds=60),
            )
            workflow.logger.info(
                "workflow.package_persisted workflow_id=%s run_id=%s case_id=%s package_id=%s",
                info.workflow_id,
                info.run_id,
                self._case_id,
                package_id,
            )
            return await _run_submission_step(
                package_id=package_id,
                initial_request_id=None,
                initial_result=None,
            )

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
