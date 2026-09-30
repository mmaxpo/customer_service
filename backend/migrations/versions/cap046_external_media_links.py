"""add customer-service external media links

Revision ID: cap046
Revises: cap045
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "cap046"
down_revision = "cap045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_external_media_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "attachment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "external_account_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "external_message_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "provider_media_id",
            sa.String(length=512),
            nullable=False,
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["cs_conversations.id"],
            name=("fk_cs_external_media_links_conversation_id_cs_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["cs_conversation_messages.id"],
            name=("fk_cs_external_media_links_message_id_cs_conversation_messages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["attachment_id"],
            ["cs_attachments.id"],
            name=("fk_cs_external_media_links_attachment_id_cs_attachments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_cs_external_media_links",
        ),
        sa.UniqueConstraint(
            "user_id",
            "channel",
            "external_account_id",
            "external_message_id",
            "provider_media_id",
            name="uq_cs_external_media",
        ),
        sa.UniqueConstraint(
            "attachment_id",
            name=("uq_cs_external_media_links_attachment_id"),
        ),
    )

    op.create_index(
        "ix_cs_external_media_links_user_id",
        "cs_external_media_links",
        ["user_id"],
    )

    op.create_index(
        "ix_cs_external_media_links_conversation_id",
        "cs_external_media_links",
        ["conversation_id"],
    )

    op.create_index(
        "ix_cs_external_media_links_message_id",
        "cs_external_media_links",
        ["message_id"],
    )

    op.create_index(
        "ix_cs_external_media_links_attachment_id",
        "cs_external_media_links",
        ["attachment_id"],
    )

    op.create_index(
        "ix_cs_external_media_links_channel",
        "cs_external_media_links",
        ["channel"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cs_external_media_links_channel",
        table_name="cs_external_media_links",
    )
    op.drop_index(
        "ix_cs_external_media_links_attachment_id",
        table_name="cs_external_media_links",
    )
    op.drop_index(
        "ix_cs_external_media_links_message_id",
        table_name="cs_external_media_links",
    )
    op.drop_index(
        "ix_cs_external_media_links_conversation_id",
        table_name="cs_external_media_links",
    )
    op.drop_index(
        "ix_cs_external_media_links_user_id",
        table_name="cs_external_media_links",
    )
    op.drop_table("cs_external_media_links")
