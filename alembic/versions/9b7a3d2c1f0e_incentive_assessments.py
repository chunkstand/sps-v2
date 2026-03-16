"""incentive_assessments

Revision ID: 9b7a3d2c1f0e
Revises: e1c2f4b5a6c7
Create Date: 2026-03-15 22:10:00.000000

Adds incentive_assessments table for Phase 5 incentive fixtures.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9b7a3d2c1f0e"
down_revision: Union[str, Sequence[str], None] = "e1c2f4b5a6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create incentive_assessments table."""
    op.create_table(
        "incentive_assessments",
        sa.Column("incentive_assessment_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("candidate_programs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("eligibility_status", sa.Text(), nullable=False),
        sa.Column("stacking_conflicts", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("deadlines", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_ids", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("advisory_value_range", sa.Text(), nullable=True),
        sa.Column("authoritative_value_state", sa.Text(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("incentive_assessment_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_incentive_assessments_case_id",
        ),
    )
    op.create_index(
        "ix_incentive_assessments_case_id",
        "incentive_assessments",
        ["case_id"],
    )


def downgrade() -> None:
    """Drop incentive_assessments table."""
    op.drop_index("ix_incentive_assessments_case_id", table_name="incentive_assessments")
    op.drop_table("incentive_assessments")
