"""admin source rules governance

Revision ID: b7c2d9e4f1a3
Revises: 37a1384857bd, e3a9c4b7d2f1
Create Date: 2026-03-16 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b7c2d9e4f1a3"
down_revision: Union[str, Sequence[str], None] = ("37a1384857bd", "e3a9c4b7d2f1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "source_rules",
        sa.Column("source_rule_id", sa.Text(), nullable=False),
        sa.Column("rule_scope", sa.Text(), nullable=False),
        sa.Column("rule_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("source_rule_id"),
        sa.UniqueConstraint("rule_scope", name="uq_source_rules_scope"),
    )
    op.create_index("ix_source_rules_scope", "source_rules", ["rule_scope"], unique=False)

    op.create_table(
        "admin_source_rule_intents",
        sa.Column("intent_id", sa.Text(), nullable=False),
        sa.Column("rule_scope", sa.Text(), nullable=False),
        sa.Column("rule_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        "ix_admin_source_rule_intents_scope",
        "admin_source_rule_intents",
        ["rule_scope"],
        unique=False,
    )
    op.create_index(
        "ix_admin_source_rule_intents_status",
        "admin_source_rule_intents",
        ["status"],
        unique=False,
    )

    op.create_table(
        "admin_source_rule_reviews",
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
            ["admin_source_rule_intents.intent_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("review_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_admin_source_rule_reviews_idempotency"),
    )
    op.create_index(
        "ix_admin_source_rule_reviews_intent",
        "admin_source_rule_reviews",
        ["intent_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_admin_source_rule_reviews_intent", table_name="admin_source_rule_reviews")
    op.drop_table("admin_source_rule_reviews")

    op.drop_index("ix_admin_source_rule_intents_status", table_name="admin_source_rule_intents")
    op.drop_index("ix_admin_source_rule_intents_scope", table_name="admin_source_rule_intents")
    op.drop_table("admin_source_rule_intents")

    op.drop_index("ix_source_rules_scope", table_name="source_rules")
    op.drop_table("source_rules")
