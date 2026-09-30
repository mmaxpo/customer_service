"""add conversation message source identity

Revision ID: cap016
Revises: cap015
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap016"
down_revision = "cap015"
branch_labels = None
depends_on = None


TABLE = "cs_conversation_messages"
INDEX = "uq_cs_conversation_messages_source_identity"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "source_type",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.add_column(
        TABLE,
        sa.Column(
            "source_message_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_index(
        INDEX,
        TABLE,
        [
            "conversation_id",
            "source_type",
            "source_message_id",
        ],
        unique=True,
        postgresql_where=sa.text(
            "source_message_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE)

    op.drop_column(
        TABLE,
        "source_message_id",
    )

    op.drop_column(
        TABLE,
        "source_type",
    )
