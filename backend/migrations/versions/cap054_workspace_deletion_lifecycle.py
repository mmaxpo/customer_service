"""add lifecycle fields for delayed workspace deletion

Revision ID: cap054
Revises: cap053
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap054"
down_revision = "cap053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("workspaces", sa.Column("deletion_scheduled_for", sa.DateTime(timezone=True), nullable=True))
    op.add_column("workspaces", sa.Column("deletion_requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_workspaces_deletion_requested_by_user",
        "workspaces", "user", ["deletion_requested_by_user_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_workspaces_deletion_scheduled_for", "workspaces", ["deletion_scheduled_for"])


def downgrade() -> None:
    op.drop_index("ix_workspaces_deletion_scheduled_for", table_name="workspaces")
    op.drop_constraint("fk_workspaces_deletion_requested_by_user", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "deletion_requested_by_user_id")
    op.drop_column("workspaces", "deletion_scheduled_for")
    op.drop_column("workspaces", "deletion_requested_at")
