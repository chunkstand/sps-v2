from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReviewerQueueItemResponse(BaseModel):
    """Queue item payload for reviewer console surfaces."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)

    case_state: str = Field(min_length=1)
    review_state: str = Field(min_length=1)
    submission_mode: str = Field(min_length=1)
    portal_support_level: str = Field(min_length=1)
    current_release_profile: str = Field(min_length=1)
    legal_hold: bool

    created_at: datetime | None = None
    updated_at: datetime | None = None

    address: str = Field(min_length=1)
    parcel_id: str | None = None
    project_type: str = Field(min_length=1)
    system_size_kw: float
    battery_flag: bool
    service_upgrade_flag: bool
    trenching_flag: bool
    structural_modification_flag: bool
    roof_type: str | None = None
    occupancy_classification: str | None = None
    utility_name: str | None = None


class ReviewerQueueResponse(BaseModel):
    """List response for reviewer queue."""

    model_config = ConfigDict(extra="forbid")

    cases: list[ReviewerQueueItemResponse]


class EvidenceArtifactMetadataResponse(BaseModel):
    """Evidence artifact metadata for reviewer evidence summaries."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    artifact_class: str = Field(min_length=1)
    producing_service: str | None = None
    linked_case_id: str | None = None
    linked_object_id: str | None = None
    authoritativeness: str = Field(min_length=1)
    retention_class: str = Field(min_length=1)
    checksum: str = Field(min_length=1)
    storage_uri: str = Field(min_length=1)
    content_bytes: int | None = None
    content_type: str | None = None
    provenance: dict[str, Any] | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class ReviewDecisionSummaryResponse(BaseModel):
    """Review decision summary for reviewer evidence surfaces."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    reviewer_independence_status: str = Field(min_length=1)
    decision_at: datetime | None = None


class EvidenceSummaryResponse(BaseModel):
    """Aggregated evidence summary for a case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    artifacts: list[EvidenceArtifactMetadataResponse] = Field(default_factory=list)
    review_decisions: list[ReviewDecisionSummaryResponse] = Field(default_factory=list)
    evidence_count: int = 0
    artifact_count: int = 0
    review_decision_count: int = 0
