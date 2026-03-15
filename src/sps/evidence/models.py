from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from sps.evidence.ids import assert_valid_evidence_id


class ArtifactClass(StrEnum):
    REQUIREMENT_EVIDENCE = "REQUIREMENT_EVIDENCE"
    COMPLIANCE_REPORT = "COMPLIANCE_REPORT"
    INCENTIVE_REPORT = "INCENTIVE_REPORT"
    DOCUMENT = "DOCUMENT"
    MANIFEST = "MANIFEST"
    RECEIPT = "RECEIPT"
    AUDIT_EVENT = "AUDIT_EVENT"
    REVIEW_RECORD = "REVIEW_RECORD"
    INCIDENT_RECORD = "INCIDENT_RECORD"
    OVERRIDE_RECORD = "OVERRIDE_RECORD"


class RetentionClass(StrEnum):
    CASE_CORE_7Y = "CASE_CORE_7Y"
    CASE_CORE_EXTENDED = "CASE_CORE_EXTENDED"
    LEGAL_HOLD = "LEGAL_HOLD"
    TRANSIENT_CACHE = "TRANSIENT_CACHE"
    RELEASE_EVIDENCE = "RELEASE_EVIDENCE"


class EvidenceArtifact(BaseModel):
    """Typed EvidenceArtifact aligned to `model/sps/contracts/evidence-artifact.schema.json`."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(...)
    artifact_class: ArtifactClass
    producing_service: str

    linked_case_id: str | None = None
    linked_object_id: str | None = None

    retention_class: RetentionClass
    checksum: str
    storage_uri: str

    authoritativeness: str
    provenance: dict[str, Any]

    created_at: dt.datetime
    expires_at: dt.datetime | None = None
    legal_hold_flag: bool

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return assert_valid_evidence_id(value)
