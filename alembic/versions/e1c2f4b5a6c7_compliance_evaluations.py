"""compliance_evaluations

Revision ID: e1c2f4b5a6c7
Revises: b2c4f7e8a901
Create Date: 2026-03-15 21:55:00.000000

Adds compliance_evaluations table for Phase 5 compliance fixtures.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e1c2f4b5a6c7"
down_revision: Union[str, Sequence[str], None] = "b2c4f7e8a901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create compliance_evaluations table."""
    op.create_table(
        "compliance_evaluations",
        sa.Column("compliance_evaluation_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("blockers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("compliance_evaluation_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_compliance_evaluations_case_id",
        ),
    )
    op.create_index(
        "ix_compliance_evaluations_case_id",
        "compliance_evaluations",
        ["case_id"],
    )


def downgrade() -> None:
    """Drop compliance_evaluations table."""
    op.drop_index("ix_compliance_evaluations_case_id", table_name="compliance_evaluations")
    op.drop_table("compliance_evaluations")
