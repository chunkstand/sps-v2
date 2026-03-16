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
