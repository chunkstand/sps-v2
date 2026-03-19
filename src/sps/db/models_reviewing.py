from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .models_base import Base


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

    __table_args__ = (sa.Index("ix_review_decisions_object", "object_type", "object_id"),)


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
