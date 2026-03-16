from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sps.workflows.permit_case.contracts import CaseState


class SiteAddress(BaseModel):
    """Structured site address from intake payload."""

    model_config = ConfigDict(extra="forbid")

    line1: str = Field(min_length=1)
    line2: str | None = None
    city: str = Field(min_length=1)
    state: str = Field(min_length=1)
    postal_code: str = Field(min_length=1)


class Requester(BaseModel):
    """Requester contact (stored as metadata, never logged)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    email: str = Field(min_length=3)


class CreateCaseRequest(BaseModel):
    """Spec-aligned CreateCase payload with normalized project fields."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1)
    intake_mode: str = Field(min_length=1)
    project_description: str = Field(min_length=1)

    site_address: SiteAddress
    requester: Requester

    # Normalized Project fields (aligned to model/sps/model.yaml)
    project_type: str = Field(min_length=1)
    system_size_kw: float = Field(gt=0)
    battery_flag: bool
    service_upgrade_flag: bool
    trenching_flag: bool
    structural_modification_flag: bool

    parcel_id: str | None = None
    roof_type: str | None = None
    occupancy_classification: str | None = None
    utility_name: str | None = None


class CreateCaseResponse(BaseModel):
    """Response for POST /api/v1/cases."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    project_id: str
    case_state: CaseState
