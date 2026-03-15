from __future__ import annotations

# Force-load pydantic_core during workflow module import to avoid Temporal workflow
# sandbox warnings about late imports (which can signal replay/determinism hazards).
import pydantic_core  # noqa: F401

from enum import Enum

from pydantic import BaseModel, Field


class PermitCaseWorkflowInput(BaseModel):
    """Stable workflow input contract.

    Keep this minimal; anything that can change frequently should be looked up in
    activities (or fetched by a caller before starting the workflow).
    """

    case_id: str = Field(min_length=1)


class ReviewDecisionOutcome(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"


class ReviewDecisionSignal(BaseModel):
    """Signal payload contract for unblocking the workflow."""

    decision_outcome: ReviewDecisionOutcome
    reviewer_id: str = Field(min_length=1)
    notes: str | None = None
