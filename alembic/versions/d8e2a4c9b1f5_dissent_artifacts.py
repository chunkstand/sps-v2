"""dissent_artifacts

Revision ID: d8e2a4c9b1f5
Revises: f3a1b9c2d7e4
Create Date: 2026-03-15 19:45:00.000000

Creates the dissent_artifacts table to durably persist dissent records
linked to ACCEPT_WITH_DISSENT review decisions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8e2a4c9b1f5'
down_revision: Union[str, Sequence[str], None] = 'f3a1b9c2d7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the dissent_artifacts table."""
    op.create_table(
        'dissent_artifacts',
        sa.Column('dissent_id', sa.Text(), nullable=False),
        sa.Column('linked_review_id', sa.Text(), nullable=False),
        sa.Column('case_id', sa.Text(), nullable=False),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('required_followup', sa.Text(), nullable=True),
        sa.Column('resolution_state', sa.Text(), nullable=False, server_default='OPEN'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint('dissent_id'),
        sa.UniqueConstraint('linked_review_id', name='uq_dissent_artifacts_linked_review_id'),
        sa.ForeignKeyConstraint(
            ['linked_review_id'],
            ['review_decisions.decision_id'],
            ondelete='RESTRICT',
            name='fk_dissent_artifacts_linked_review_id',
        ),
        sa.ForeignKeyConstraint(
            ['case_id'],
            ['permit_cases.case_id'],
            ondelete='CASCADE',
            name='fk_dissent_artifacts_case_id',
        ),
    )
    op.create_index(
        'ix_dissent_artifacts_case_id',
        'dissent_artifacts',
        ['case_id'],
    )


def downgrade() -> None:
    """Drop the dissent_artifacts table."""
    op.drop_index('ix_dissent_artifacts_case_id', table_name='dissent_artifacts')
    op.drop_table('dissent_artifacts')
