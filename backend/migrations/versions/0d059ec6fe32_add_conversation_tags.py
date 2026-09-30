"""add conversation tags

Revision ID: 0d059ec6fe32
Revises: e0966f68a0bd
Create Date: 2026-05-26 17:52:00.190029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0d059ec6fe32'
down_revision: Union[str, Sequence[str], None] = 'e0966f68a0bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.create_table(
        "cs_conversation_tags",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "conversation_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
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
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_cs_conversation_tags_user_id",
        "cs_conversation_tags",
        ["user_id"],
    )

    op.create_index(
        "ix_cs_conversation_tags_conversation_id",
        "cs_conversation_tags",
        ["conversation_id"],
    )

    op.create_index(
        "ix_cs_conversation_tags_name",
        "cs_conversation_tags",
        ["name"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
