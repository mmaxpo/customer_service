"""customer service omnichannel foundation

Revision ID: oc1a000000001
Revises: b76a968166e5
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "oc1a000000001"
down_revision = "b76a968166e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_channel_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "channel", "external_account_id", name="uq_cs_channel_connection_account"),
    )
    op.create_index("ix_cs_channel_connections_user_id", "cs_channel_connections", ["user_id"])
    op.create_index("ix_cs_channel_connections_channel", "cs_channel_connections", ["channel"])

    op.create_table(
        "cs_external_conversation_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_conversations.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_customers.id"), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=False),
        sa.Column("external_thread_id", sa.String(length=255), nullable=False),
        sa.Column("external_customer_id", sa.String(length=255), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "channel", "external_account_id", "external_thread_id", name="uq_cs_external_conversation_thread"),
    )
    op.create_index("ix_cs_external_conversation_links_user_id", "cs_external_conversation_links", ["user_id"])
    op.create_index("ix_cs_external_conversation_links_conversation_id", "cs_external_conversation_links", ["conversation_id"])
    op.create_index("ix_cs_external_conversation_links_customer_id", "cs_external_conversation_links", ["customer_id"])
    op.create_index("ix_cs_external_conversation_links_channel", "cs_external_conversation_links", ["channel"])

    op.create_table(
        "cs_external_message_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_conversations.id"), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_conversation_messages.id"), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=False),
        sa.Column("external_thread_id", sa.String(length=255), nullable=False),
        sa.Column("external_message_id", sa.String(length=255), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False, server_default="inbound"),
        sa.Column("delivery_status", sa.String(length=64), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "channel", "external_account_id", "external_message_id", name="uq_cs_external_message"),
    )
    op.create_index("ix_cs_external_message_links_user_id", "cs_external_message_links", ["user_id"])
    op.create_index("ix_cs_external_message_links_conversation_id", "cs_external_message_links", ["conversation_id"])
    op.create_index("ix_cs_external_message_links_message_id", "cs_external_message_links", ["message_id"])
    op.create_index("ix_cs_external_message_links_channel", "cs_external_message_links", ["channel"])


def downgrade() -> None:
    op.drop_index("ix_cs_external_message_links_channel", table_name="cs_external_message_links")
    op.drop_index("ix_cs_external_message_links_message_id", table_name="cs_external_message_links")
    op.drop_index("ix_cs_external_message_links_conversation_id", table_name="cs_external_message_links")
    op.drop_index("ix_cs_external_message_links_user_id", table_name="cs_external_message_links")
    op.drop_table("cs_external_message_links")

    op.drop_index("ix_cs_external_conversation_links_channel", table_name="cs_external_conversation_links")
    op.drop_index("ix_cs_external_conversation_links_customer_id", table_name="cs_external_conversation_links")
    op.drop_index("ix_cs_external_conversation_links_conversation_id", table_name="cs_external_conversation_links")
    op.drop_index("ix_cs_external_conversation_links_user_id", table_name="cs_external_conversation_links")
    op.drop_table("cs_external_conversation_links")

    op.drop_index("ix_cs_channel_connections_channel", table_name="cs_channel_connections")
    op.drop_index("ix_cs_channel_connections_user_id", table_name="cs_channel_connections")
    op.drop_table("cs_channel_connections")
