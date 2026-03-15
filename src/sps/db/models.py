from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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
