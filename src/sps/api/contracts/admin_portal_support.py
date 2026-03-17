from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdminPortalSupportIntentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1)
    portal_family: str = Field(min_length=1)
    requested_support_level: str = Field(min_length=1)
    intent_payload: dict[str, Any]
    requested_by: str = Field(min_length=1)


class AdminPortalSupportIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    portal_family: str
    requested_support_level: str
    status: str
    created_at: datetime | None = None


class AdminPortalSupportReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    decision_outcome: str = Field(min_length=1)
    review_payload: dict[str, Any] | None = None
    idempotency_key: str = Field(min_length=1)


class AdminPortalSupportReviewDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    intent_id: str
    decision_outcome: str
    idempotency_key: str
    reviewed_at: datetime | None = None


class AdminPortalSupportApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    portal_support_metadata_id: str
    portal_family: str
    support_level: str
    applied_at: datetime | None = None
