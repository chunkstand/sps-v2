from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .models_base import Base


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
