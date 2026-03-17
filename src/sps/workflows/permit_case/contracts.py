from __future__ import annotations

# Force-load pydantic_core during workflow module import to avoid Temporal workflow
# sandbox warnings about late imports (which can signal replay/determinism hazards).
import pydantic_core  # noqa: F401

import datetime as dt
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class PermitCaseWorkflowInput(BaseModel):
    """Stable workflow input contract.

    Keep this minimal; anything that can change frequently should be looked up in
    activities (or fetched by a caller before starting the workflow).
    """

    case_id: str = Field(min_length=1)


class ReviewDecisionOutcome(str, Enum):
    """Canonical ReviewDecision.decision_outcome enum.

    Aligned to: model/sps/contracts/review-decision.schema.json
    """

    ACCEPT = "ACCEPT"
    ACCEPT_WITH_DISSENT = "ACCEPT_WITH_DISSENT"
    BLOCK = "BLOCK"


class ReviewerIndependenceStatus(str, Enum):
    """Canonical ReviewDecision.reviewer_independence_status enum."""

    PASS = "PASS"
    WARNING = "WARNING"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    BLOCKED = "BLOCKED"
    OVERRIDE_APPLIED = "OVERRIDE_APPLIED"


class ReviewDecisionSignal(BaseModel):
    """Signal payload contract for unblocking the workflow."""

    model_config = ConfigDict(extra="forbid")

    decision_outcome: ReviewDecisionOutcome
    reviewer_id: str = Field(min_length=1)

    # The canonical ReviewDecision contract requires this field. We default it for
    # operator ergonomics; callers can override when needed.
    reviewer_independence_status: ReviewerIndependenceStatus = ReviewerIndependenceStatus.PASS

    evidence_ids: list[str] = Field(default_factory=list)
    contradiction_resolution: str | None = None
    notes: str | None = None

    # Added in M003-S01: the API-issued decision_id is carried in the signal so
    # the workflow can reference the already-persisted ReviewDecision row without
    # an additional DB round-trip.  Defaults to None for backward compatibility
    # with existing workflows and tests that omit this field.
    decision_id: str | None = None


class CaseState(str, Enum):
    """Authoritative PermitCase.case_state enum (contract-aligned)."""

    DRAFT = "DRAFT"
    INTAKE_PENDING = "INTAKE_PENDING"
    INTAKE_COMPLETE = "INTAKE_COMPLETE"
    JURISDICTION_PENDING = "JURISDICTION_PENDING"
    JURISDICTION_COMPLETE = "JURISDICTION_COMPLETE"
    RESEARCH_PENDING = "RESEARCH_PENDING"
    RESEARCH_COMPLETE = "RESEARCH_COMPLETE"
    COMPLIANCE_PENDING = "COMPLIANCE_PENDING"
    COMPLIANCE_COMPLETE = "COMPLIANCE_COMPLETE"
    INCENTIVES_PENDING = "INCENTIVES_PENDING"
    INCENTIVES_COMPLETE = "INCENTIVES_COMPLETE"
    DOCUMENT_PENDING = "DOCUMENT_PENDING"
    DOCUMENT_COMPLETE = "DOCUMENT_COMPLETE"
    REVIEW_PENDING = "REVIEW_PENDING"
    BLOCKED = "BLOCKED"
    APPROVED_FOR_SUBMISSION = "APPROVED_FOR_SUBMISSION"
    SUBMISSION_PENDING = "SUBMISSION_PENDING"
    SUBMITTED = "SUBMITTED"
    COMMENT_REVIEW_PENDING = "COMMENT_REVIEW_PENDING"
    CORRECTION_PENDING = "CORRECTION_PENDING"
    RESUBMISSION_PENDING = "RESUBMISSION_PENDING"
    APPROVED = "APPROVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    MANUAL_SUBMISSION_REQUIRED = "MANUAL_SUBMISSION_REQUIRED"
    EMERGENCY_HOLD = "EMERGENCY_HOLD"
    ROLLED_BACK = "ROLLED_BACK"


class ExternalStatusClass(str, Enum):
    """Canonical ExternalStatusEvent.normalized_status enum."""

    RECEIVED_UNCONFIRMED = "RECEIVED_UNCONFIRMED"
    RECEIVED_CONFIRMED = "RECEIVED_CONFIRMED"
    IN_REVIEW = "IN_REVIEW"
    COMMENT_ISSUED = "COMMENT_ISSUED"
    RESUBMISSION_REQUESTED = "RESUBMISSION_REQUESTED"
    APPROVAL_REPORTED = "APPROVAL_REPORTED"
    APPROVAL_CONFIRMED = "APPROVAL_CONFIRMED"
    APPROVAL_PENDING_INSPECTION = "APPROVAL_PENDING_INSPECTION"
    APPROVAL_FINAL = "APPROVAL_FINAL"
    INSPECTION_SCHEDULED = "INSPECTION_SCHEDULED"
    INSPECTION_PASSED = "INSPECTION_PASSED"
    INSPECTION_FAILED = "INSPECTION_FAILED"
    REJECTION_REPORTED = "REJECTION_REPORTED"
    WITHDRAWN_REPORTED = "WITHDRAWN_REPORTED"
    CLOSED_REPORTED = "CLOSED_REPORTED"
    UNKNOWN_EXTERNAL_STATUS = "UNKNOWN_EXTERNAL_STATUS"
    CONTRADICTORY_EXTERNAL_STATUS = "CONTRADICTORY_EXTERNAL_STATUS"


class ExternalStatusConfidence(str, Enum):
    """Confidence rating for external status normalization."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class ActorType(str, Enum):
    planner = "planner"
    specialist_worker = "specialist_worker"
    reviewer = "reviewer"
    operator = "operator"
    release_manager = "release_manager"
    system_guard = "system_guard"


class StateTransitionRequest(BaseModel):
    """Guarded case-state transition request (contract-aligned).

    This model is aligned to: model/sps/contracts/state-transition-request.schema.json
    """

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)

    from_state: CaseState
    to_state: CaseState

    actor_type: ActorType
    actor_id: str = Field(min_length=1)

    correlation_id: str = Field(min_length=1)
    causation_id: str | None = None

    required_review_id: str | None = None
    required_evidence_ids: list[str]

    override_id: str | None = None
    requested_at: dt.datetime
    notes: str | None = None


class PersistJurisdictionResolutionRequest(BaseModel):
    """Activity input for persisting jurisdiction resolution fixtures."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)


class PersistRequirementSetRequest(BaseModel):
    """Activity input for persisting requirement set fixtures."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)


class PersistComplianceEvaluationRequest(BaseModel):
    """Activity input for persisting compliance evaluation fixtures."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)


class PersistIncentiveAssessmentRequest(BaseModel):
    """Activity input for persisting incentive assessment fixtures."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)


class PersistCorrectionTaskRequest(BaseModel):
    """Activity input for persisting correction task artifacts from external status events."""

    model_config = ConfigDict(extra="forbid")

    correction_task_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    submission_attempt_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    summary: str | None = None
    requested_at: dt.datetime | None = None
    due_at: dt.datetime | None = None


class PersistResubmissionPackageRequest(BaseModel):
    """Activity input for persisting resubmission package artifacts from external status events."""

    model_config = ConfigDict(extra="forbid")

    resubmission_package_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    submission_attempt_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    package_version: str = Field(min_length=1)
    status: str = Field(min_length=1)
    submitted_at: dt.datetime | None = None


class PersistApprovalRecordRequest(BaseModel):
    """Activity input for persisting approval record artifacts from external status events."""

    model_config = ConfigDict(extra="forbid")

    approval_record_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    submission_attempt_id: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    authority: str | None = None
    decided_at: dt.datetime | None = None


class PersistInspectionMilestoneRequest(BaseModel):
    """Activity input for persisting inspection milestone artifacts from external status events."""

    model_config = ConfigDict(extra="forbid")

    inspection_milestone_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    submission_attempt_id: str = Field(min_length=1)
    milestone_type: str = Field(min_length=1)
    status: str = Field(min_length=1)
    scheduled_for: dt.datetime | None = None
    completed_at: dt.datetime | None = None


class ExternalStatusNormalizationRequest(BaseModel):
    """Activity input for normalizing and persisting external status events."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    submission_attempt_id: str = Field(min_length=1)
    raw_status: str = Field(min_length=1)
    received_at: dt.datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ExternalStatusNormalizationResult(BaseModel):
    """Normalized external status event payload."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    case_id: str
    submission_attempt_id: str
    raw_status: str
    normalized_status: ExternalStatusClass
    confidence: ExternalStatusConfidence
    auto_advance_eligible: bool
    evidence_ids: list[str] = Field(default_factory=list)
    mapping_version: str
    received_at: dt.datetime


class PermitCaseStateSnapshot(BaseModel):
    """Activity payload for PermitCase state branching."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    case_state: CaseState
    project_id: str = Field(min_length=1)


class AppliedStateTransitionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: Literal["applied"] = "applied"
    event_type: str
    applied_at: dt.datetime


class DeniedStateTransitionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: Literal["denied"] = "denied"
    event_type: str
    denied_at: dt.datetime

    denial_reason: str

    # When a governance guard assertion applies, we persist stable IDs here.
    guard_assertion_id: str | None = None
    normalized_business_invariants: list[str] | None = None


StateTransitionResult = AppliedStateTransitionResult | DeniedStateTransitionResult

_state_transition_result_adapter = TypeAdapter(StateTransitionResult)


def parse_state_transition_result(payload: object) -> StateTransitionResult:
    """Parse a JSON payload back into a typed StateTransitionResult."""

    return _state_transition_result_adapter.validate_python(payload)


class PersistReviewDecisionRequest(BaseModel):
    """Activity input for durable ReviewDecision persistence.

    Uses ReviewDecision.idempotency_key as the idempotency boundary.
    """

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    schema_version: str = Field(default="1.0.0", min_length=1)

    case_id: str = Field(min_length=1)
    object_type: Literal["PermitCase"] = "PermitCase"
    object_id: str = Field(min_length=1)

    decision_outcome: ReviewDecisionOutcome
    reviewer_id: str = Field(min_length=1)
    reviewer_independence_status: ReviewerIndependenceStatus

    evidence_ids: list[str] = Field(default_factory=list)
    contradiction_resolution: str | None = None

    dissent_flag: bool
    notes: str | None = None

    decision_at: dt.datetime

    idempotency_key: str = Field(min_length=1)


class PersistSubmissionPackageRequest(BaseModel):
    """Activity input for persisting submission package + document artifacts."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)


class SubmissionAdapterOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    UNSUPPORTED_WORKFLOW = "UNSUPPORTED_WORKFLOW"
    FAILED = "FAILED"


class SubmissionAdapterRequest(BaseModel):
    """Activity input for deterministic submission adapter execution."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    submission_attempt_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    manifest_id: str = Field(min_length=1)
    target_portal_family: str = Field(min_length=1)
    artifact_digests: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)
    attempt_number: int = Field(default=1, ge=1)
    correlation_id: str = Field(min_length=1)


class SubmissionAdapterResult(BaseModel):
    """Outcome payload for deterministic submission adapter execution."""

    model_config = ConfigDict(extra="forbid")

    submission_attempt_id: str
    status: str
    outcome: SubmissionAdapterOutcome
    external_tracking_id: str | None = None
    receipt_artifact_id: str | None = None
    submitted_at: dt.datetime | None = None
    manual_fallback_package_id: str | None = None
    portal_support_level: str | None = None
    failure_class: str | None = None


def submission_attempt_id_for_workflow(*, workflow_id: str, run_id: str, attempt: int) -> str:
    return f"{workflow_id}/{run_id}/submission_attempt/attempt-{attempt}"


def submission_attempt_idempotency_key(*, case_id: str, attempt: int) -> str:
    return f"submit/{case_id}/attempt-{attempt}"


def manual_fallback_package_id_for_workflow(*, workflow_id: str, run_id: str, attempt: int) -> str:
    return f"{workflow_id}/{run_id}/manual_fallback/attempt-{attempt}"


class PermitCaseWorkflowResult(BaseModel):
    """Workflow completion payload.

    Includes the correlation tuple and the intake or review guarded transition attempts.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    correlation_id: str

    intake_request_id: str | None = None
    intake_result: StateTransitionResult | None = None

    initial_request_id: str
    initial_result: StateTransitionResult

    review_decision_id: str | None = None
    review_signal: ReviewDecisionSignal | None = None

    final_request_id: str
    final_result: StateTransitionResult
