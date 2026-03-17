"""post_submission_artifacts

Revision ID: b1c2d3e4f5a6
Revises: a9b3c2d4e6f7
Create Date: 2026-03-16 15:59:00.000000

Add correction_tasks, resubmission_packages, approval_records, inspection_milestones tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a9b3c2d4e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create post-submission artifact tables."""
    op.create_table(
        "correction_tasks",
        sa.Column("correction_task_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("submission_attempt_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("correction_task_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_correction_tasks_case_id",
        ),
        sa.ForeignKeyConstraint(
            ["submission_attempt_id"],
            ["submission_attempts.submission_attempt_id"],
            ondelete="RESTRICT",
            name="fk_correction_tasks_submission_attempt_id",
        ),
    )
    op.create_index(
        "ix_correction_tasks_case_id",
        "correction_tasks",
        ["case_id"],
    )
    op.create_index(
        "ix_correction_tasks_submission_attempt_id",
        "correction_tasks",
        ["submission_attempt_id"],
    )

    op.create_table(
        "resubmission_packages",
        sa.Column("resubmission_package_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("submission_attempt_id", sa.Text(), nullable=False),
        sa.Column("package_id", sa.Text(), nullable=False),
        sa.Column("package_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("resubmission_package_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_resubmission_packages_case_id",
        ),
        sa.ForeignKeyConstraint(
            ["submission_attempt_id"],
            ["submission_attempts.submission_attempt_id"],
            ondelete="RESTRICT",
            name="fk_resubmission_packages_submission_attempt_id",
        ),
    )
    op.create_index(
        "ix_resubmission_packages_case_id",
        "resubmission_packages",
        ["case_id"],
    )
    op.create_index(
        "ix_resubmission_packages_submission_attempt_id",
        "resubmission_packages",
        ["submission_attempt_id"],
    )

    op.create_table(
        "approval_records",
        sa.Column("approval_record_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("submission_attempt_id", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("authority", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("approval_record_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_approval_records_case_id",
        ),
        sa.ForeignKeyConstraint(
            ["submission_attempt_id"],
            ["submission_attempts.submission_attempt_id"],
            ondelete="RESTRICT",
            name="fk_approval_records_submission_attempt_id",
        ),
    )
    op.create_index(
        "ix_approval_records_case_id",
        "approval_records",
        ["case_id"],
    )
    op.create_index(
        "ix_approval_records_submission_attempt_id",
        "approval_records",
        ["submission_attempt_id"],
    )

    op.create_table(
        "inspection_milestones",
        sa.Column("inspection_milestone_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("submission_attempt_id", sa.Text(), nullable=False),
        sa.Column("milestone_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("inspection_milestone_id"),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["permit_cases.case_id"],
            ondelete="RESTRICT",
            name="fk_inspection_milestones_case_id",
        ),
        sa.ForeignKeyConstraint(
            ["submission_attempt_id"],
            ["submission_attempts.submission_attempt_id"],
            ondelete="RESTRICT",
            name="fk_inspection_milestones_submission_attempt_id",
        ),
    )
    op.create_index(
        "ix_inspection_milestones_case_id",
        "inspection_milestones",
        ["case_id"],
    )
    op.create_index(
        "ix_inspection_milestones_submission_attempt_id",
        "inspection_milestones",
        ["submission_attempt_id"],
    )


def downgrade() -> None:
    """Drop post-submission artifact tables."""
    op.drop_index("ix_inspection_milestones_submission_attempt_id", table_name="inspection_milestones")
    op.drop_index("ix_inspection_milestones_case_id", table_name="inspection_milestones")
    op.drop_table("inspection_milestones")

    op.drop_index("ix_approval_records_submission_attempt_id", table_name="approval_records")
    op.drop_index("ix_approval_records_case_id", table_name="approval_records")
    op.drop_table("approval_records")

    op.drop_index("ix_resubmission_packages_submission_attempt_id", table_name="resubmission_packages")
    op.drop_index("ix_resubmission_packages_case_id", table_name="resubmission_packages")
    op.drop_table("resubmission_packages")

    op.drop_index("ix_correction_tasks_submission_attempt_id", table_name="correction_tasks")
    op.drop_index("ix_correction_tasks_case_id", table_name="correction_tasks")
    op.drop_table("correction_tasks")
