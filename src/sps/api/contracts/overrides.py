from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateOverrideRequest(BaseModel):
    """Payload for POST /api/v1/overrides."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    justification: str = Field(min_length=1)
    duration_hours: int = Field(gt=0)
    affected_surfaces: list[str] = Field(min_length=1)


class OverrideResponse(BaseModel):
    """Response shape for override artifact creation."""

    model_config = ConfigDict(extra="forbid")

    override_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    approver_id: str = Field(min_length=1)
    start_at: datetime
    expires_at: datetime
    affected_surfaces: list[str]
    created_at: datetime
