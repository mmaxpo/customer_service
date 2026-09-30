"""add workspace settings audit log

Revision ID: cap051
Revises: cap050
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap051"
down_revision = "cap050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_settings_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_settings_audit_logs_workspace_id",
        "workspace_settings_audit_logs",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_settings_audit_logs_actor_user_id",
        "workspace_settings_audit_logs",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_workspace_settings_audit_logs_action",
        "workspace_settings_audit_logs",
        ["action"],
    )
    op.create_index(
        "ix_workspace_settings_audit_logs_workspace_created",
        "workspace_settings_audit_logs",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_settings_audit_logs_workspace_created",
        table_name="workspace_settings_audit_logs",
    )
    op.drop_index(
        "ix_workspace_settings_audit_logs_action",
        table_name="workspace_settings_audit_logs",
    )
    op.drop_index(
        "ix_workspace_settings_audit_logs_actor_user_id",
        table_name="workspace_settings_audit_logs",
    )
    op.drop_index(
        "ix_workspace_settings_audit_logs_workspace_id",
        table_name="workspace_settings_audit_logs",
    )
    op.drop_table("workspace_settings_audit_logs")
