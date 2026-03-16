from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JurisdictionResolutionResponse(BaseModel):
    """Jurisdiction resolution payload for case read surfaces."""

    model_config = ConfigDict(extra="forbid")

    jurisdiction_resolution_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)

    city_authority_id: str | None = None
    county_authority_id: str | None = None
    state_authority_id: str | None = None
    utility_authority_id: str | None = None

    zoning_district: str | None = None
    overlays: list[str] | None = None
    permitting_portal_family: str | None = None

    support_level: str = Field(min_length=1)
    manual_requirements: list[str] | None = None

    evidence_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class RequirementSetResponse(BaseModel):
    """Requirement set payload for case read surfaces."""

    model_config = ConfigDict(extra="forbid")

    requirement_set_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)

    jurisdiction_ids: list[str] = Field(default_factory=list)
    permit_types: list[str] = Field(default_factory=list)
    forms_required: list[str] = Field(default_factory=list)
    attachments_required: list[str] = Field(default_factory=list)

    fee_rules: list[dict[str, Any]] | None = None
    source_rankings: list[dict[str, Any]] = Field(default_factory=list)

    freshness_state: str = Field(min_length=1)
    freshness_expires_at: datetime
    contradiction_state: str = Field(min_length=1)

    evidence_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class ComplianceEvaluationResponse(BaseModel):
    """Compliance evaluation payload for case read surfaces."""

    model_config = ConfigDict(extra="forbid")

    compliance_evaluation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)

    schema_version: str = Field(min_length=1)
    evaluated_at: datetime

    rule_results: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)

    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class IncentiveAssessmentResponse(BaseModel):
    """Incentive assessment payload for case read surfaces."""

    model_config = ConfigDict(extra="forbid")

    incentive_assessment_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)

    schema_version: str = Field(min_length=1)
    assessed_at: datetime

    candidate_programs: list[dict[str, Any]] = Field(default_factory=list)
    eligibility_status: str = Field(min_length=1)
    stacking_conflicts: list[str] = Field(default_factory=list)
    deadlines: list[dict[str, Any]] | None = None
    source_ids: list[str] = Field(default_factory=list)
    advisory_value_range: str | None = None
    authoritative_value_state: str = Field(min_length=1)

    provenance: dict[str, Any] | None = None
    evidence_payload: dict[str, Any] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class JurisdictionResolutionListResponse(BaseModel):
    """List response for jurisdiction resolutions per case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    jurisdictions: list[JurisdictionResolutionResponse]


class RequirementSetListResponse(BaseModel):
    """List response for requirement sets per case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    requirement_sets: list[RequirementSetResponse]


class ComplianceEvaluationListResponse(BaseModel):
    """List response for compliance evaluations per case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    compliance_evaluations: list[ComplianceEvaluationResponse]


class IncentiveAssessmentListResponse(BaseModel):
    """List response for incentive assessments per case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    incentive_assessments: list[IncentiveAssessmentResponse]


class DocumentReferenceResponse(BaseModel):
    """Document reference in a submission manifest."""
    
    model_config = ConfigDict(extra="forbid")
    
    document_id: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    sha256_digest: str = Field(min_length=1)


class SubmissionManifestResponse(BaseModel):
    """Submission manifest payload for case read surfaces."""
    
    model_config = ConfigDict(extra="forbid")
    
    manifest_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    package_version: str = Field(min_length=1)
    generated_at: datetime
    document_references: list[DocumentReferenceResponse]
    required_attachments: list[str] = Field(default_factory=list)
    target_portal_family: str = Field(min_length=1)
    provenance: dict[str, Any] | None = None


class SubmissionPackageResponse(BaseModel):
    """Submission package payload for case read surfaces."""
    
    model_config = ConfigDict(extra="forbid")
    
    package_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    package_version: str = Field(min_length=1)
    manifest_artifact_id: str = Field(min_length=1)
    manifest_sha256_digest: str = Field(min_length=1)
    provenance: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

