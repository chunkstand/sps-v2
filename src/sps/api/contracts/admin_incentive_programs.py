from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdminIncentiveProgramIntentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1)
    program_key: str = Field(min_length=1)
    program_payload: dict[str, Any]
    requested_by: str = Field(min_length=1)


class AdminIncentiveProgramIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    program_key: str
    status: str
    created_at: datetime | None = None


class AdminIncentiveProgramReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    decision_outcome: str = Field(min_length=1)
    review_payload: dict[str, Any] | None = None
    idempotency_key: str = Field(min_length=1)


class AdminIncentiveProgramReviewDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    intent_id: str
    decision_outcome: str
    idempotency_key: str
    reviewed_at: datetime | None = None


class AdminIncentiveProgramApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    incentive_program_id: str
    program_key: str
    applied_at: datetime | None = None
