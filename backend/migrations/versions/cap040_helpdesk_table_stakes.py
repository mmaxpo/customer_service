"""Add sellable helpdesk table-stakes state.

Revision ID: cap040
Revises: cap039
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap040"
down_revision = "cap039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cs_customers",
        sa.Column(
            "custom_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "cs_conversations", sa.Column("snoozed_until", sa.DateTime(timezone=True))
    )
    op.add_column(
        "cs_conversations", sa.Column("snooze_reason", sa.String(length=255))
    )
    op.add_column(
        "cs_conversations", sa.Column("snoozed_by_user_id", sa.UUID())
    )
    op.add_column(
        "cs_conversations",
        sa.Column(
            "moderation_status",
            sa.String(length=32),
            nullable=False,
            server_default="normal",
        ),
    )
    op.add_column(
        "cs_conversations", sa.Column("moderation_reason", sa.String(length=500))
    )
    op.add_column(
        "cs_conversations",
        sa.Column("moderation_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_cs_conversations_snoozed_by_user",
        "cs_conversations",
        "user",
        ["snoozed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_cs_conversations_snoozed_until", "cs_conversations", ["snoozed_until"]
    )
    op.create_index(
        "ix_cs_conversations_moderation_status",
        "cs_conversations",
        ["moderation_status"],
    )
    op.create_table(
        "cs_reply_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("author_user_id", sa.UUID()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("sent_message_id", sa.UUID()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["cs_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sent_message_id"], ["cs_conversation_messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cs_reply_drafts_workspace_id", "cs_reply_drafts", ["workspace_id"])
    op.create_index("ix_cs_reply_drafts_conversation_id", "cs_reply_drafts", ["conversation_id"])
    op.create_index("ix_cs_reply_drafts_status", "cs_reply_drafts", ["status"])
    op.create_index(
        "ix_cs_reply_drafts_workspace_conversation_status",
        "cs_reply_drafts",
        ["workspace_id", "conversation_id", "status"],
    )
    op.create_table(
        "cs_reply_signatures",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("scope_key", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.UUID()),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "scope_key", name="uq_cs_reply_signature_workspace_scope"
        ),
    )
    op.create_index("ix_cs_reply_signatures_workspace_id", "cs_reply_signatures", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_cs_reply_signatures_workspace_id", table_name="cs_reply_signatures")
    op.drop_table("cs_reply_signatures")
    op.drop_index("ix_cs_reply_drafts_workspace_conversation_status", table_name="cs_reply_drafts")
    op.drop_index("ix_cs_reply_drafts_status", table_name="cs_reply_drafts")
    op.drop_index("ix_cs_reply_drafts_conversation_id", table_name="cs_reply_drafts")
    op.drop_index("ix_cs_reply_drafts_workspace_id", table_name="cs_reply_drafts")
    op.drop_table("cs_reply_drafts")
    op.drop_index("ix_cs_conversations_moderation_status", table_name="cs_conversations")
    op.drop_index("ix_cs_conversations_snoozed_until", table_name="cs_conversations")
    op.drop_constraint("fk_cs_conversations_snoozed_by_user", "cs_conversations", type_="foreignkey")
    op.drop_column("cs_conversations", "moderation_score")
    op.drop_column("cs_conversations", "moderation_reason")
    op.drop_column("cs_conversations", "moderation_status")
    op.drop_column("cs_conversations", "snoozed_by_user_id")
    op.drop_column("cs_conversations", "snooze_reason")
    op.drop_column("cs_conversations", "snoozed_until")
    op.drop_column("cs_customers", "custom_fields")
