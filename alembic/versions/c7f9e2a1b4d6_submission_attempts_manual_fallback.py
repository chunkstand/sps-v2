"""submission_attempts_manual_fallback

Revision ID: c7f9e2a1b4d6
Revises: a1b2c3d4e5f6
Create Date: 2026-03-16 10:55:00.000000

Adds submission_attempts and manual_fallback_packages tables for deterministic
submission tracking and manual fallback persistence.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c7f9e2a1b4d6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create submission_attempts and manual_fallback_packages tables."""
    op.create_table(
        "submission_attempts",
        sa.Column("submission_attempt_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("package_id", sa.Text(), nullable=False),
        sa.Column("manifest_artifact_id", sa.Text(), nullable=False),
        sa.Column("target_portal_family", sa.Text(), nullable=False),
        sa.Column("portal_support_level", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("external_tracking_id", sa.Text(), nullable=True),
        sa.Column("receipt_artifact_id", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_class", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("submission_attempt_id"),
        sa.UniqueConstraint("request_id", name="uq_submission_attempts_request_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_submission_attempts_idempotency_key"),
        sa.UniqueConstraint(
            "case_id",
            "attempt_number",
            name="uq_submission_attempts_case_attempt_number",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_submission_attempts_case_id",
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["submission_packages.package_id"],
            ondelete="RESTRICT",
            name="fk_submission_attempts_package_id",
        ),
        sa.ForeignKeyConstraint(
            ["manifest_artifact_id"],
            ["evidence_artifacts.artifact_id"],
            ondelete="RESTRICT",
            name="fk_submission_attempts_manifest_artifact_id",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_artifact_id"],
            ["evidence_artifacts.artifact_id"],
            ondelete="RESTRICT",
            name="fk_submission_attempts_receipt_artifact_id",
        ),
    )
    op.create_index(
        "ix_submission_attempts_case_id",
        "submission_attempts",
        ["case_id"],
    )
    op.create_index(
        "ix_submission_attempts_package_id",
        "submission_attempts",
        ["package_id"],
    )

    op.create_table(
        "manual_fallback_packages",
        sa.Column("manual_fallback_package_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("package_id", sa.Text(), nullable=False),
        sa.Column("submission_attempt_id", sa.Text(), nullable=True),
        sa.Column("package_version", sa.Text(), nullable=False),
        sa.Column("package_hash", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("portal_support_level", sa.Text(), nullable=False),
        sa.Column("channel_type", sa.Text(), nullable=False),
        sa.Column(
            "proof_bundle_state",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'PENDING_REVIEW'"),
        ),
        sa.Column("required_attachments", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("operator_instructions", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("required_proof_types", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("escalation_owner", sa.Text(), nullable=True),
        sa.Column("proof_bundle_artifact_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("manual_fallback_package_id"),
        sa.UniqueConstraint(
            "case_id",
            "package_id",
            "package_version",
            name="uq_manual_fallback_packages_case_package_version",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_manual_fallback_packages_case_id",
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["submission_packages.package_id"],
            ondelete="RESTRICT",
            name="fk_manual_fallback_packages_package_id",
        ),
        sa.ForeignKeyConstraint(
            ["submission_attempt_id"],
            ["submission_attempts.submission_attempt_id"],
            ondelete="RESTRICT",
            name="fk_manual_fallback_packages_submission_attempt_id",
        ),
        sa.ForeignKeyConstraint(
            ["proof_bundle_artifact_id"],
            ["evidence_artifacts.artifact_id"],
            ondelete="RESTRICT",
            name="fk_manual_fallback_packages_proof_bundle_artifact_id",
        ),
    )
    op.create_index(
        "ix_manual_fallback_packages_case_id",
        "manual_fallback_packages",
        ["case_id"],
    )
    op.create_index(
        "ix_manual_fallback_packages_package_id",
        "manual_fallback_packages",
        ["package_id"],
    )
    op.create_index(
        "ix_manual_fallback_packages_submission_attempt_id",
        "manual_fallback_packages",
        ["submission_attempt_id"],
    )


def downgrade() -> None:
    """Drop submission_attempts and manual_fallback_packages tables."""
    op.drop_index("ix_manual_fallback_packages_submission_attempt_id", table_name="manual_fallback_packages")
    op.drop_index("ix_manual_fallback_packages_package_id", table_name="manual_fallback_packages")
    op.drop_index("ix_manual_fallback_packages_case_id", table_name="manual_fallback_packages")
    op.drop_table("manual_fallback_packages")

    op.drop_index("ix_submission_attempts_package_id", table_name="submission_attempts")
    op.drop_index("ix_submission_attempts_case_id", table_name="submission_attempts")
    op.drop_table("submission_attempts")
