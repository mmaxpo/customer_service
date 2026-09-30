"""add customer service inbox hot path indexes

Revision ID: csi000000001
Revises: 66c4bf99457a
Create Date: 2026-06-16
"""

from typing import Sequence, Union

from alembic import op


revision: str = "csi000000001"
down_revision: Union[str, None] = "66c4bf99457a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_cs_conversations_user_updated_id",
        "cs_conversations",
        ["user_id", "updated_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_cs_conversation_messages_conversation_created_id",
        "cs_conversation_messages",
        ["conversation_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cs_conversation_messages_conversation_created_id",
        table_name="cs_conversation_messages",
    )
    op.drop_index(
        "ix_cs_conversations_user_updated_id",
        table_name="cs_conversations",
    )
