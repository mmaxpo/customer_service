"""customer service phase2 suggested actions

Revision ID: d76f18b8b1d3
Revises: f2a000000001
Create Date: 2026-05-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d76f18b8b1d3"
down_revision: Union[str, Sequence[str], None] = "f2a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "cs_suggested_actions",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
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
            "action_type",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),

        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),

        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="suggested",
        ),

        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default="rule",
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),

        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["cs_conversations.id"],
        ),
    )

    op.create_index(
        "ix_cs_suggested_actions_user_id",
        "cs_suggested_actions",
        ["user_id"],
    )

    op.create_index(
        "ix_cs_suggested_actions_conversation_id",
        "cs_suggested_actions",
        ["conversation_id"],
    )

    op.create_index(
        "ix_cs_suggested_actions_action_type",
        "cs_suggested_actions",
        ["action_type"],
    )

    op.create_index(
        "ix_cs_suggested_actions_status",
        "cs_suggested_actions",
        ["status"],
    )


def downgrade() -> None:

    op.drop_index(
        "ix_cs_suggested_actions_status",
        table_name="cs_suggested_actions",
    )

    op.drop_index(
        "ix_cs_suggested_actions_action_type",
        table_name="cs_suggested_actions",
    )

    op.drop_index(
        "ix_cs_suggested_actions_conversation_id",
        table_name="cs_suggested_actions",
    )

    op.drop_index(
        "ix_cs_suggested_actions_user_id",
        table_name="cs_suggested_actions",
    )

    op.drop_table(
        "cs_suggested_actions"
    )