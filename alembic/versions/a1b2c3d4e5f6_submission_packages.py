"""submission_packages

Revision ID: a1b2c3d4e5f6
Revises: 9b7a3d2c1f0e
Create Date: 2026-03-16 08:56:00.000000

Adds submission_packages and document_artifacts tables for Phase 6 document generation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9b7a3d2c1f0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create submission_packages and document_artifacts tables."""
    op.create_table(
        "submission_packages",
        sa.Column("package_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("package_version", sa.Text(), nullable=False),
        sa.Column("manifest_artifact_id", sa.Text(), nullable=False),
        sa.Column("manifest_sha256_digest", sa.Text(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("package_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_submission_packages_case_id",
        ),
        sa.ForeignKeyConstraint(
            ["manifest_artifact_id"],
            ["evidence_artifacts.artifact_id"],
            ondelete="RESTRICT",
            name="fk_submission_packages_manifest_artifact_id",
        ),
    )
    op.create_index(
        "ix_submission_packages_case_id",
        "submission_packages",
        ["case_id"],
    )

    op.create_table(
        "document_artifacts",
        sa.Column("document_artifact_id", sa.Text(), nullable=False),
        sa.Column("package_id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("template_name", sa.Text(), nullable=False),
        sa.Column("evidence_artifact_id", sa.Text(), nullable=False),
        sa.Column("sha256_digest", sa.Text(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("document_artifact_id"),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["submission_packages.package_id"],
            ondelete="RESTRICT",
            name="fk_document_artifacts_package_id",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_artifact_id"],
            ["evidence_artifacts.artifact_id"],
            ondelete="RESTRICT",
            name="fk_document_artifacts_evidence_artifact_id",
        ),
    )
    op.create_index(
        "ix_document_artifacts_package_id",
        "document_artifacts",
        ["package_id"],
    )


def downgrade() -> None:
    """Drop submission_packages and document_artifacts tables."""
    op.drop_index("ix_document_artifacts_package_id", table_name="document_artifacts")
    op.drop_table("document_artifacts")
    op.drop_index("ix_submission_packages_case_id", table_name="submission_packages")
    op.drop_table("submission_packages")
