from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from sps.documents.contracts import DocumentType

T = TypeVar("T")


@dataclass(frozen=True)
class AdapterResult(Generic[T]):
    source_kind: str
    source_key: str
    value: T


@dataclass(frozen=True)
class RuntimeAdapterMetadata:
    adapter_key: str
    version: str


class JurisdictionResolutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jurisdiction_resolution_id: str
    case_id: str
    city_authority_id: str | None = None
    county_authority_id: str | None = None
    state_authority_id: str | None = None
    utility_authority_id: str | None = None
    zoning_district: str | None = None
    overlays: list[str] | None = None
    permitting_portal_family: str | None = None
    support_level: str
    manual_requirements: list[str] | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None


class RequirementSetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_set_id: str
    case_id: str
    jurisdiction_ids: list[str]
    permit_types: list[str]
    forms_required: list[str]
    attachments_required: list[str]
    fee_rules: list[dict[str, Any]] | None = None
    source_rankings: list[dict[str, Any]]
    freshness_state: str
    freshness_expires_at: datetime
    contradiction_state: str
    evidence_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None


class ComplianceEvaluationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compliance_evaluation_id: str
    case_id: str
    schema_version: str
    evaluated_at: datetime
    rule_results: list[dict[str, Any]]
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None


class DocumentTemplateSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: DocumentType
    template_name: str
    template_path: Path
    variables: dict[str, Any]
    provenance: dict[str, Any] | None = None


class DocumentCompilationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_set_id: str
    case_id: str
    package_version: str
    target_portal_family: str
    required_attachments: list[str] = Field(default_factory=list)
    documents: list[DocumentTemplateSpec]
    provenance: dict[str, Any] | None = None


class SubmissionExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    target_portal_family: str
    channel_type: str
    reason: str | None = None
    operator_instructions: list[str] = Field(default_factory=list)
    required_proof_types: list[str] = Field(default_factory=list)
    required_attachment_sources: list[str] = Field(default_factory=list)
    escalation_owner: str | None = None


class ExternalStatusMappingEntryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_status: str
    normalized_status: str
    confidence: str
    allowed_case_states: list[str] = Field(default_factory=list)
    auto_advance: bool = False
    required_evidence: list[str] = Field(default_factory=list)
    reviewer_confirmation_required: bool = False
    contradiction_triggers: list[str] = Field(default_factory=list)


class ExternalStatusMappingSelectionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_family: str
    mapping_version: str
    mappings: dict[str, ExternalStatusMappingEntryRecord]


class JurisdictionAdapter(Protocol):
    def load(self, case_id: str) -> AdapterResult[list[JurisdictionResolutionRecord]]: ...


class RequirementsAdapter(Protocol):
    def load(self, case_id: str) -> AdapterResult[list[RequirementSetRecord]]: ...


class ComplianceAdapter(Protocol):
    def load(self, case_id: str) -> AdapterResult[list[ComplianceEvaluationRecord]]: ...


class DocumentAdapter(Protocol):
    def load(self, case_id: str) -> AdapterResult[DocumentCompilationSpec]: ...


class SubmissionAdapter(Protocol):
    def load(self, case_id: str, *, target_portal_family: str) -> AdapterResult[SubmissionExecutionPlan | None]: ...


class StatusMappingAdapter(Protocol):
    def load(self, case_id: str) -> AdapterResult[ExternalStatusMappingSelectionRecord]: ...


class RuntimeAdapterSlice(Protocol):
    METADATA: RuntimeAdapterMetadata

    def supports_case(self, case_id: str) -> bool: ...

    def load_jurisdiction(self, case_id: str) -> AdapterResult[list[JurisdictionResolutionRecord]]: ...

    def load_requirements(self, case_id: str) -> AdapterResult[list[RequirementSetRecord]]: ...

    def load_compliance(self, case_id: str) -> AdapterResult[list[ComplianceEvaluationRecord]]: ...

    def load_documents(self, case_id: str) -> AdapterResult[DocumentCompilationSpec]: ...

    def load_submission(
        self,
        case_id: str,
        *,
        target_portal_family: str,
    ) -> AdapterResult[SubmissionExecutionPlan | None]: ...

    def load_status_mapping(self, case_id: str) -> AdapterResult[ExternalStatusMappingSelectionRecord]: ...
