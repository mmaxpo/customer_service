"""Remember which workspace a user last chose (set when they accept an invitation).

Revision ID: ui02
Revises: ui01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ui02"
down_revision = "ui01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("active_workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_active_workspace_id_workspaces",
        "user",
        "workspaces",
        ["active_workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_user_active_workspace_id_workspaces", "user", type_="foreignkey")
    op.drop_column("user", "active_workspace_id")
