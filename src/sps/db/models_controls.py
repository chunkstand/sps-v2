from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .models_base import Base


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

    __table_args__ = (sa.Index("ix_emergency_records_case_expires", "case_id", "expires_at"),)


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

    __table_args__ = (sa.Index("ix_override_artifacts_case_expires", "case_id", "expires_at"),)


class PortalSupportMetadata(Base):
    __tablename__ = "portal_support_metadata"

    portal_support_metadata_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    portal_family: Mapped[str] = mapped_column(sa.Text, nullable=False)
    support_level: Mapped[str] = mapped_column(sa.Text, nullable=False)
    metadata_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("portal_family", name="uq_portal_support_metadata_family"),
        sa.Index("ix_portal_support_metadata_family", "portal_family"),
    )


class SourceRule(Base):
    __tablename__ = "source_rules"

    source_rule_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    rule_scope: Mapped[str] = mapped_column(sa.Text, nullable=False)
    rule_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("rule_scope", name="uq_source_rules_scope"),
        sa.Index("ix_source_rules_scope", "rule_scope"),
    )


class IncentiveProgram(Base):
    __tablename__ = "incentive_programs"

    incentive_program_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    program_key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    program_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("program_key", name="uq_incentive_programs_key"),
        sa.Index("ix_incentive_programs_key", "program_key"),
    )


class AdminIncentiveProgramIntent(Base):
    __tablename__ = "admin_incentive_program_intents"

    intent_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    program_key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    program_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'PENDING_REVIEW'"))
    requested_by: Mapped[str] = mapped_column(sa.Text, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.Index("ix_admin_incentive_program_intents_key", "program_key"),
        sa.Index("ix_admin_incentive_program_intents_status", "status"),
    )


class AdminIncentiveProgramReview(Base):
    __tablename__ = "admin_incentive_program_reviews"

    review_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    intent_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("admin_incentive_program_intents.intent_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    decision_outcome: Mapped[str] = mapped_column(sa.Text, nullable=False)
    review_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)

    reviewed_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (sa.Index("ix_admin_incentive_program_reviews_intent", "intent_id"),)


class AdminSourceRuleIntent(Base):
    __tablename__ = "admin_source_rule_intents"

    intent_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    rule_scope: Mapped[str] = mapped_column(sa.Text, nullable=False)
    rule_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'PENDING_REVIEW'"))
    requested_by: Mapped[str] = mapped_column(sa.Text, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.Index("ix_admin_source_rule_intents_scope", "rule_scope"),
        sa.Index("ix_admin_source_rule_intents_status", "status"),
    )


class AdminSourceRuleReview(Base):
    __tablename__ = "admin_source_rule_reviews"

    review_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    intent_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("admin_source_rule_intents.intent_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    decision_outcome: Mapped[str] = mapped_column(sa.Text, nullable=False)
    review_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)

    reviewed_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (sa.Index("ix_admin_source_rule_reviews_intent", "intent_id"),)


class AdminPortalSupportIntent(Base):
    __tablename__ = "admin_portal_support_intents"

    intent_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    portal_family: Mapped[str] = mapped_column(sa.Text, nullable=False)
    requested_support_level: Mapped[str] = mapped_column(sa.Text, nullable=False)
    intent_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'PENDING_REVIEW'"))
    requested_by: Mapped[str] = mapped_column(sa.Text, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.Index("ix_admin_portal_support_intents_family", "portal_family"),
        sa.Index("ix_admin_portal_support_intents_status", "status"),
    )


class AdminPortalSupportReview(Base):
    __tablename__ = "admin_portal_support_reviews"

    review_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    intent_id: Mapped[str] = mapped_column(
        sa.Text,
        sa.ForeignKey("admin_portal_support_intents.intent_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    decision_outcome: Mapped[str] = mapped_column(sa.Text, nullable=False)
    review_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)

    reviewed_at: Mapped[dt.datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (sa.Index("ix_admin_portal_support_reviews_intent", "intent_id"),)
