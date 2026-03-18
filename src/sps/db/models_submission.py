from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .models_base import Base


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

    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'PENDING'"))
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
        sa.UniqueConstraint("case_id", "attempt_number", name="uq_submission_attempts_case_attempt_number"),
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

    required_attachments: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    operator_instructions: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
    required_proof_types: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
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
        sa.UniqueConstraint("case_id", "package_id", "package_version", name="uq_manual_fallback_packages_case_package_version"),
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
