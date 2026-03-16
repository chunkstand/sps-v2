"""external_status_events

Revision ID: f0b4c9d7e2a1
Revises: c7f9e2a1b4d6
Create Date: 2026-03-16 11:25:00.000000

Adds external_status_events table for normalized external status tracking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f0b4c9d7e2a1"
down_revision: Union[str, Sequence[str], None] = "c7f9e2a1b4d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create external_status_events table."""
    op.create_table(
        "external_status_events",
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("submission_attempt_id", sa.Text(), nullable=False),
        sa.Column("raw_status", sa.Text(), nullable=False),
        sa.Column("normalized_status", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Text(), nullable=False),
        sa.Column("auto_advance_eligible", sa.Boolean(), nullable=False),
        sa.Column("evidence_ids", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("mapping_version", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_external_status_events_case_id",
        ),
        sa.ForeignKeyConstraint(
            ["submission_attempt_id"],
            ["submission_attempts.submission_attempt_id"],
            ondelete="RESTRICT",
            name="fk_external_status_events_submission_attempt_id",
        ),
    )
    op.create_index(
        "ix_external_status_events_case_id",
        "external_status_events",
        ["case_id"],
    )
    op.create_index(
        "ix_external_status_events_submission_attempt_id",
        "external_status_events",
        ["submission_attempt_id"],
    )


def downgrade() -> None:
    """Drop external_status_events table."""
    op.drop_index("ix_external_status_events_submission_attempt_id", table_name="external_status_events")
    op.drop_index("ix_external_status_events_case_id", table_name="external_status_events")
    op.drop_table("external_status_events")
