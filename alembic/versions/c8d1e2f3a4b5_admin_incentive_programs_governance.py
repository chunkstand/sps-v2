"""admin incentive programs governance

Revision ID: c8d1e2f3a4b5
Revises: b7c2d9e4f1a3
Create Date: 2026-03-16 21:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c8d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "b7c2d9e4f1a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "incentive_programs",
        sa.Column("incentive_program_id", sa.Text(), nullable=False),
        sa.Column("program_key", sa.Text(), nullable=False),
        sa.Column("program_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("incentive_program_id"),
        sa.UniqueConstraint("program_key", name="uq_incentive_programs_key"),
    )
    op.create_index("ix_incentive_programs_key", "incentive_programs", ["program_key"], unique=False)

    op.create_table(
        "admin_incentive_program_intents",
        sa.Column("intent_id", sa.Text(), nullable=False),
        sa.Column("program_key", sa.Text(), nullable=False),
        sa.Column("program_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'PENDING_REVIEW'"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("intent_id"),
    )
    op.create_index(
        "ix_admin_incentive_program_intents_key",
        "admin_incentive_program_intents",
        ["program_key"],
        unique=False,
    )
    op.create_index(
        "ix_admin_incentive_program_intents_status",
        "admin_incentive_program_intents",
        ["status"],
        unique=False,
    )

    op.create_table(
        "admin_incentive_program_reviews",
        sa.Column("review_id", sa.Text(), nullable=False),
        sa.Column("intent_id", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.Text(), nullable=False),
        sa.Column("decision_outcome", sa.Text(), nullable=False),
        sa.Column("review_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["intent_id"],
            ["admin_incentive_program_intents.intent_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("review_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_admin_incentive_program_reviews_idempotency"),
    )
    op.create_index(
        "ix_admin_incentive_program_reviews_intent",
        "admin_incentive_program_reviews",
        ["intent_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_admin_incentive_program_reviews_intent", table_name="admin_incentive_program_reviews")
    op.drop_table("admin_incentive_program_reviews")

    op.drop_index("ix_admin_incentive_program_intents_status", table_name="admin_incentive_program_intents")
    op.drop_index("ix_admin_incentive_program_intents_key", table_name="admin_incentive_program_intents")
    op.drop_table("admin_incentive_program_intents")

    op.drop_index("ix_incentive_programs_key", table_name="incentive_programs")
    op.drop_table("incentive_programs")
