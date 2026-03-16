"""jurisdiction_requirements

Revision ID: b2c4f7e8a901
Revises: d8e2a4c9b1f5
Create Date: 2026-03-15 21:50:00.000000

Creates jurisdiction_resolutions and requirement_sets tables for Phase 4 fixtures.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2c4f7e8a901"
down_revision: Union[str, Sequence[str], None] = "d8e2a4c9b1f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create jurisdiction_resolutions and requirement_sets tables."""
    op.create_table(
        "jurisdiction_resolutions",
        sa.Column("jurisdiction_resolution_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("city_authority_id", sa.Text(), nullable=True),
        sa.Column("county_authority_id", sa.Text(), nullable=True),
        sa.Column("state_authority_id", sa.Text(), nullable=True),
        sa.Column("utility_authority_id", sa.Text(), nullable=True),
        sa.Column("zoning_district", sa.Text(), nullable=True),
        sa.Column("overlays", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("permitting_portal_family", sa.Text(), nullable=True),
        sa.Column("support_level", sa.Text(), nullable=False),
        sa.Column("manual_requirements", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("evidence_ids", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("jurisdiction_resolution_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_jurisdiction_resolutions_case_id",
        ),
    )
    op.create_index(
        "ix_jurisdiction_resolutions_case_id",
        "jurisdiction_resolutions",
        ["case_id"],
    )

    op.create_table(
        "requirement_sets",
        sa.Column("requirement_set_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("jurisdiction_ids", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("permit_types", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("forms_required", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("attachments_required", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("fee_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_rankings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("freshness_state", sa.Text(), nullable=False),
        sa.Column("freshness_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contradiction_state", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("requirement_set_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_requirement_sets_case_id",
        ),
    )
    op.create_index(
        "ix_requirement_sets_case_id",
        "requirement_sets",
        ["case_id"],
    )


def downgrade() -> None:
    """Drop requirement_sets and jurisdiction_resolutions tables."""
    op.drop_index("ix_requirement_sets_case_id", table_name="requirement_sets")
    op.drop_table("requirement_sets")
    op.drop_index("ix_jurisdiction_resolutions_case_id", table_name="jurisdiction_resolutions")
    op.drop_table("jurisdiction_resolutions")
