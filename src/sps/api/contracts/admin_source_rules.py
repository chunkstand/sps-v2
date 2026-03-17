from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdminSourceRuleIntentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1)
    rule_scope: str = Field(min_length=1)
    rule_payload: dict[str, Any]
    requested_by: str = Field(min_length=1)


class AdminSourceRuleIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    rule_scope: str
    status: str
    created_at: datetime | None = None


class AdminSourceRuleReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    decision_outcome: str = Field(min_length=1)
    review_payload: dict[str, Any] | None = None
    idempotency_key: str = Field(min_length=1)


class AdminSourceRuleReviewDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    intent_id: str
    decision_outcome: str
    idempotency_key: str
    reviewed_at: datetime | None = None


class AdminSourceRuleApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    source_rule_id: str
    rule_scope: str
    applied_at: datetime | None = None
