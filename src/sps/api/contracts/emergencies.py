from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateEmergencyRequest(BaseModel):
    """Payload for POST /api/v1/emergencies."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    allowed_bypasses: list[str] = Field(default_factory=list)
    forbidden_bypasses: list[str] = Field(default_factory=list)
    duration_hours: int | None = None


class EmergencyResponse(BaseModel):
    """Response shape for emergency declaration."""

    model_config = ConfigDict(extra="forbid")

    emergency_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    declared_by: str = Field(min_length=1)
    started_at: datetime
    expires_at: datetime
    cleanup_due_at: datetime | None
    created_at: datetime
