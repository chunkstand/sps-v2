from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    correlation_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True, index=True)

    actor_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    action: Mapped[str] = mapped_column(sa.Text, nullable=False)

    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


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


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    decision_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    schema_version: Mapped[str] = mapped_column(sa.Text, nullable=False)

    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    object_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    object_id: Mapped[str] = mapped_column(sa.Text, nullable=False)

    decision_outcome: Mapped[str] = mapped_column(sa.Text, nullable=False)
    reviewer_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    subject_author_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    reviewer_independence_status: Mapped[str] = mapped_column(sa.Text, nullable=False)

    evidence_ids: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")

    contradiction_resolution: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    dissent_flag: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    decision_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.Index("ix_review_decisions_object", "object_type", "object_id"),
    )


class ContradictionArtifact(Base):
    __tablename__ = "contradiction_artifacts"

    contradiction_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    scope: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source_a: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source_b: Mapped[str] = mapped_column(sa.Text, nullable=False)
    ranking_relation: Mapped[str] = mapped_column(sa.Text, nullable=False)
    blocking_effect: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    resolution_status: Mapped[str] = mapped_column(sa.Text, nullable=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class DissentArtifact(Base):
    __tablename__ = "dissent_artifacts"

    dissent_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    linked_review_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("review_decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="CASCADE"), nullable=False, index=True
    )

    scope: Mapped[str] = mapped_column(sa.Text, nullable=False)
    rationale: Mapped[str] = mapped_column(sa.Text, nullable=False)
    required_followup: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    resolution_state: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'OPEN'"))

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class CaseTransitionLedger(Base):
    __tablename__ = "case_transition_ledger"

    transition_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    event_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    from_state: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    to_state: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    actor_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True, index=True)

    occurred_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifacts"

    artifact_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)

    artifact_class: Mapped[str] = mapped_column(sa.Text, nullable=False)
    producing_service: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    linked_case_id: Mapped[str | None] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    linked_object_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True, index=True)

    authoritativeness: Mapped[str] = mapped_column(sa.Text, nullable=False)
    retention_class: Mapped[str] = mapped_column(sa.Text, nullable=False)

    checksum: Mapped[str] = mapped_column(sa.Text, nullable=False)
    storage_uri: Mapped[str] = mapped_column(sa.Text, nullable=False)

    content_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    content_type: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    expires_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    legal_hold_flag: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))


class LegalHold(Base):
    __tablename__ = "legal_holds"

    hold_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)

    reason: Mapped[str] = mapped_column(sa.Text, nullable=False)
    requested_by: Mapped[str] = mapped_column(sa.Text, nullable=False)
    authorized_by: Mapped[str] = mapped_column(sa.Text, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    released_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'ACTIVE'"))


class LegalHoldBinding(Base):
    __tablename__ = "legal_hold_bindings"

    binding_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)

    hold_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("legal_holds.hold_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Exactly one of these should be set.
    artifact_id: Mapped[str | None] = mapped_column(
        sa.Text,
        sa.ForeignKey("evidence_artifacts.artifact_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    case_id: Mapped[str | None] = mapped_column(
        sa.Text,
        sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.CheckConstraint(
            "(artifact_id IS NOT NULL AND case_id IS NULL) OR (artifact_id IS NULL AND case_id IS NOT NULL)",
            name="ck_legal_hold_bindings_exactly_one_target",
        ),
    )


class ReleaseBundle(Base):
    __tablename__ = "release_bundles"

    release_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    spec_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    app_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    model_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    policy_bundle_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    invariant_pack_version: Mapped[str] = mapped_column(sa.Text, nullable=False)

    adapter_versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    artifact_digests: Mapped[dict] = mapped_column(JSONB, nullable=False)
    approvals: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)


class ReleaseArtifact(Base):
    __tablename__ = "release_artifacts"

    artifact_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    release_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("release_bundles.release_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    checksum: Mapped[str] = mapped_column(sa.Text, nullable=False)
    storage_uri: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)


class SubmissionPackage(Base):
    __tablename__ = "submission_packages"

    package_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    package_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    manifest_artifact_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("evidence_artifacts.artifact_id", ondelete="RESTRICT"), nullable=False
    )
    manifest_sha256_digest: Mapped[str] = mapped_column(sa.Text, nullable=False)

    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class SubmissionAttempt(Base):
    __tablename__ = "submission_attempts"

    submission_attempt_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    package_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("submission_packages.package_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    manifest_artifact_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("evidence_artifacts.artifact_id", ondelete="RESTRICT"), nullable=False
    )

    target_portal_family: Mapped[str] = mapped_column(sa.Text, nullable=False)
    portal_support_level: Mapped[str] = mapped_column(sa.Text, nullable=False)

    request_id: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)
    attempt_number: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))

    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'PENDING'")
    )
    outcome: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    external_tracking_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    receipt_artifact_id: Mapped[str | None] = mapped_column(
        sa.Text, sa.ForeignKey("evidence_artifacts.artifact_id", ondelete="RESTRICT"), nullable=True
    )
    submitted_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    failure_class: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    last_error_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "case_id",
            "attempt_number",
            name="uq_submission_attempts_case_attempt_number",
        ),
    )


class ExternalStatusEvent(Base):
    __tablename__ = "external_status_events"

    event_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submission_attempt_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("submission_attempts.submission_attempt_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    raw_status: Mapped[str] = mapped_column(sa.Text, nullable=False)
    normalized_status: Mapped[str] = mapped_column(sa.Text, nullable=False)
    confidence: Mapped[str] = mapped_column(sa.Text, nullable=False)
    auto_advance_eligible: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    mapping_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    received_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class ManualFallbackPackage(Base):
    __tablename__ = "manual_fallback_packages"

    manual_fallback_package_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    package_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("submission_packages.package_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submission_attempt_id: Mapped[str | None] = mapped_column(
        sa.Text,
        sa.ForeignKey("submission_attempts.submission_attempt_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    package_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    package_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    reason: Mapped[str] = mapped_column(sa.Text, nullable=False)
    portal_support_level: Mapped[str] = mapped_column(sa.Text, nullable=False)
    channel_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    proof_bundle_state: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'PENDING_REVIEW'")
    )

    required_attachments: Mapped[list[str]] = mapped_column(
        sa.ARRAY(sa.Text), nullable=False, server_default="{}"
    )
    operator_instructions: Mapped[list[str]] = mapped_column(
        sa.ARRAY(sa.Text), nullable=False, server_default="{}"
    )
    required_proof_types: Mapped[list[str]] = mapped_column(
        sa.ARRAY(sa.Text), nullable=False, server_default="{}"
    )
    escalation_owner: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    proof_bundle_artifact_id: Mapped[str | None] = mapped_column(
        sa.Text, sa.ForeignKey("evidence_artifacts.artifact_id", ondelete="RESTRICT"), nullable=True
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "case_id",
            "package_id",
            "package_version",
            name="uq_manual_fallback_packages_case_package_version",
        ),
    )


class DocumentArtifact(Base):
    __tablename__ = "document_artifacts"

    document_artifact_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    package_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("submission_packages.package_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    document_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    document_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    template_name: Mapped[str] = mapped_column(sa.Text, nullable=False)

    evidence_artifact_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("evidence_artifacts.artifact_id", ondelete="RESTRICT"), nullable=False
    )
    sha256_digest: Mapped[str] = mapped_column(sa.Text, nullable=False)

    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class CorrectionTask(Base):
    __tablename__ = "correction_tasks"

    correction_task_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submission_attempt_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("submission_attempts.submission_attempt_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(sa.Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    requested_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    due_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class ResubmissionPackage(Base):
    __tablename__ = "resubmission_packages"

    resubmission_package_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submission_attempt_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("submission_attempts.submission_attempt_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    package_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    package_version: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False)
    submitted_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    approval_record_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submission_attempt_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("submission_attempts.submission_attempt_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    decision: Mapped[str] = mapped_column(sa.Text, nullable=False)
    authority: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    decided_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class InspectionMilestone(Base):
    __tablename__ = "inspection_milestones"

    inspection_milestone_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submission_attempt_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("submission_attempts.submission_attempt_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    milestone_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False)
    scheduled_for: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class EmergencyRecord(Base):
    __tablename__ = "emergency_records"

    emergency_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    incident_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    scope: Mapped[str] = mapped_column(sa.Text, nullable=False)
    declared_by: Mapped[str] = mapped_column(sa.Text, nullable=False)

    started_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    allowed_bypasses: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    forbidden_bypasses: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    cleanup_due_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.Index("ix_emergency_records_case_expires", "case_id", "expires_at"),
    )


class OverrideArtifact(Base):
    __tablename__ = "override_artifacts"

    override_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        sa.Text, sa.ForeignKey("permit_cases.case_id", ondelete="RESTRICT"), nullable=False, index=True
    )

    scope: Mapped[str] = mapped_column(sa.Text, nullable=False)
    justification: Mapped[str] = mapped_column(sa.Text, nullable=False)

    start_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    affected_surfaces: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    approver_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    cleanup_required: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.Index("ix_override_artifacts_case_expires", "case_id", "expires_at"),
    )
