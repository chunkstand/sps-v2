"""review_decisions subject_author_id

Revision ID: f4c2b1a9d0e3
Revises: f0b4c9d7e2a1
Create Date: 2026-03-16 10:45:00.000000

Adds subject_author_id to review_decisions for rolling-quarter reviewer independence metrics.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4c2b1a9d0e3"
down_revision: Union[str, Sequence[str], None] = "f0b4c9d7e2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add subject_author_id column to review_decisions."""
    op.add_column("review_decisions", sa.Column("subject_author_id", sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop subject_author_id column from review_decisions."""
    op.drop_column("review_decisions", "subject_author_id")
