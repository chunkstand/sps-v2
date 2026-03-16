"""contradiction_artifacts_resolved_fields

Revision ID: f3a1b9c2d7e4
Revises: a06baa922883
Create Date: 2026-03-15 19:40:00.000000

Adds resolved_at (nullable timestamptz) and resolved_by (nullable text)
to contradiction_artifacts to track resolution provenance.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1b9c2d7e4'
down_revision: Union[str, Sequence[str], None] = 'a06baa922883'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add resolved_at and resolved_by columns to contradiction_artifacts."""
    op.add_column(
        'contradiction_artifacts',
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'contradiction_artifacts',
        sa.Column('resolved_by', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove resolved_at and resolved_by columns from contradiction_artifacts."""
    op.drop_column('contradiction_artifacts', 'resolved_by')
    op.drop_column('contradiction_artifacts', 'resolved_at')
