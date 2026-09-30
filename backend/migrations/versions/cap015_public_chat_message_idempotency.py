"""add public chat message idempotency identity

Revision ID: cap015
Revises: cap014
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "cap015"
down_revision = "cap014"
branch_labels = None
depends_on = None


TABLE = "cs_chat_messages"
INDEX = "uq_cs_chat_messages_session_client_message_id"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "client_message_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        INDEX,
        TABLE,
        ["session_id", "client_message_id"],
        unique=True,
        postgresql_where=sa.text(
            "client_message_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE)
    op.drop_column(TABLE, "client_message_id")
