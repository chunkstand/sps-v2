"""Document and manifest contract models for typed generation and assembly."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    PERMIT_APPLICATION = "PERMIT_APPLICATION"
    SITE_PLAN_CHECKLIST = "SITE_PLAN_CHECKLIST"
    ELECTRICAL_DIAGRAM = "ELECTRICAL_DIAGRAM"
    STRUCTURAL_CALCS = "STRUCTURAL_CALCS"
    EQUIPMENT_SPECS = "EQUIPMENT_SPECS"


class DocumentArtifactPayload(BaseModel):
    """Typed payload for a generated document artifact."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    document_id: str
    document_type: DocumentType
    case_id: str
    template_name: str
    content_bytes: bytes
    sha256_digest: str
    generated_at: datetime
    provenance: dict[str, str | list[str]] | None = None


class ManifestDocumentReference(BaseModel):
    """Reference to a document artifact in the manifest."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: DocumentType
    artifact_id: str
    sha256_digest: str


class SubmissionManifestPayload(BaseModel):
    """Typed payload for a submission package manifest."""

    model_config = ConfigDict(extra="forbid")

    manifest_id: str
    case_id: str
    package_version: str
    generated_at: datetime
    document_references: list[ManifestDocumentReference]
    required_attachments: list[str] = Field(default_factory=list)
    target_portal_family: str
    provenance: dict[str, str] | None = None


class SubmissionPackagePayload(BaseModel):
    """Typed payload for a complete submission package with manifest + documents."""

    model_config = ConfigDict(extra="forbid")

    package_id: str
    case_id: str
    package_version: str
    manifest: SubmissionManifestPayload
    document_artifacts: list[DocumentArtifactPayload]
    manifest_sha256_digest: str
    created_at: datetime
    provenance: dict[str, str] | None = None
