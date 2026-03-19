from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .models_base import Base


class PermitCase(Base):
    __tablename__ = "permit_cases"

    case_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    project_id: Mapped[str] = mapped_column(sa.Text, nullable=False, index=True)

    case_state: Mapped[str] = mapped_column(sa.Text, nullable=False)
    review_state: Mapped[str] = mapped_column(sa.Text, nullable=False)
    submission_mode: Mapped[str] = mapped_column(sa.Text, nullable=False)
    portal_support_level: Mapped[str] = mapped_column(sa.Text, nullable=False)

    current_package_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    current_release_profile: Mapped[str] = mapped_column(sa.Text, nullable=False)

    legal_hold: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    closure_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, unique=True
    )

    address: Mapped[str] = mapped_column(sa.Text, nullable=False)
    parcel_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    project_type: Mapped[str] = mapped_column(sa.Text, nullable=False)

    system_size_kw: Mapped[float] = mapped_column(sa.Double, nullable=False)

    battery_flag: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    service_upgrade_flag: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    trenching_flag: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    structural_modification_flag: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

    roof_type: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    occupancy_classification: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    utility_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    contact_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class JurisdictionResolution(Base):
    __tablename__ = "jurisdiction_resolutions"

    jurisdiction_resolution_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    city_authority_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    county_authority_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    state_authority_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    utility_authority_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    zoning_district: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    overlays: Mapped[list[str] | None] = mapped_column(sa.ARRAY(sa.Text), nullable=True)
    permitting_portal_family: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    support_level: Mapped[str] = mapped_column(sa.Text, nullable=False)
    manual_requirements: Mapped[list[str] | None] = mapped_column(sa.ARRAY(sa.Text), nullable=True)

    evidence_ids: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class RequirementSet(Base):
    __tablename__ = "requirement_sets"

    requirement_set_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    jurisdiction_ids: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    permit_types: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    forms_required: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    attachments_required: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")

    fee_rules: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    source_rankings: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)

    freshness_state: Mapped[str] = mapped_column(sa.Text, nullable=False)
    freshness_expires_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    contradiction_state: Mapped[str] = mapped_column(sa.Text, nullable=False)

    evidence_ids: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class ComplianceEvaluation(Base):
    __tablename__ = "compliance_evaluations"

    compliance_evaluation_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    schema_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    evaluated_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    rule_results: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    blockers: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class IncentiveAssessment(Base):
    __tablename__ = "incentive_assessments"

    incentive_assessment_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    schema_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    assessed_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    candidate_programs: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    eligibility_status: Mapped[str] = mapped_column(sa.Text, nullable=False)
    stacking_conflicts: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    deadlines: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    source_ids: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    advisory_value_range: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    authoritative_value_state: Mapped[str] = mapped_column(sa.Text, nullable=False)

    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
