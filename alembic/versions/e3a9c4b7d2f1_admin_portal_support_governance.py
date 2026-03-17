"""admin portal support governance

Revision ID: e3a9c4b7d2f1
Revises: f4c2b1a9d0e3
Create Date: 2026-03-16 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e3a9c4b7d2f1"
down_revision: Union[str, Sequence[str], None] = "f4c2b1a9d0e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "portal_support_metadata",
        sa.Column("portal_support_metadata_id", sa.Text(), nullable=False),
        sa.Column("portal_family", sa.Text(), nullable=False),
        sa.Column("support_level", sa.Text(), nullable=False),
        sa.Column("metadata_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("portal_support_metadata_id"),
        sa.UniqueConstraint("portal_family", name="uq_portal_support_metadata_family"),
    )
    op.create_index(
        "ix_portal_support_metadata_family",
        "portal_support_metadata",
        ["portal_family"],
        unique=False,
    )

    op.create_table(
        "admin_portal_support_intents",
        sa.Column("intent_id", sa.Text(), nullable=False),
        sa.Column("portal_family", sa.Text(), nullable=False),
        sa.Column("requested_support_level", sa.Text(), nullable=False),
        sa.Column("intent_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        "ix_admin_portal_support_intents_family",
        "admin_portal_support_intents",
        ["portal_family"],
        unique=False,
    )
    op.create_index(
        "ix_admin_portal_support_intents_status",
        "admin_portal_support_intents",
        ["status"],
        unique=False,
    )

    op.create_table(
        "admin_portal_support_reviews",
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
            ["admin_portal_support_intents.intent_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("review_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_admin_portal_support_reviews_idempotency"),
    )
    op.create_index(
        "ix_admin_portal_support_reviews_intent",
        "admin_portal_support_reviews",
        ["intent_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_admin_portal_support_reviews_intent", table_name="admin_portal_support_reviews")
    op.drop_table("admin_portal_support_reviews")

    op.drop_index("ix_admin_portal_support_intents_status", table_name="admin_portal_support_intents")
    op.drop_index("ix_admin_portal_support_intents_family", table_name="admin_portal_support_intents")
    op.drop_table("admin_portal_support_intents")

    op.drop_index("ix_portal_support_metadata_family", table_name="portal_support_metadata")
    op.drop_table("portal_support_metadata")
