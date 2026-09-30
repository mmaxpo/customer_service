"""add customer service conversation followers

Revision ID: cap042
Revises: cap041
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap042"
down_revision = "cap041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_conversation_followers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "followed_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["cs_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["followed_by_user_id"],
            ["user.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "conversation_id",
            "user_id",
            name=("uq_cs_conversation_followers_workspace_conversation_user"),
        ),
    )

    op.create_index(
        "ix_cs_conversation_followers_workspace_id",
        "cs_conversation_followers",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_cs_conversation_followers_conversation_id",
        "cs_conversation_followers",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_cs_conversation_followers_user_id",
        "cs_conversation_followers",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        ("ix_cs_conversation_followers_workspace_conversation"),
        "cs_conversation_followers",
        ["workspace_id", "conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_cs_conversation_followers_workspace_user",
        "cs_conversation_followers",
        ["workspace_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cs_conversation_followers_workspace_user",
        table_name="cs_conversation_followers",
    )
    op.drop_index(
        ("ix_cs_conversation_followers_workspace_conversation"),
        table_name="cs_conversation_followers",
    )
    op.drop_index(
        "ix_cs_conversation_followers_user_id",
        table_name="cs_conversation_followers",
    )
    op.drop_index(
        "ix_cs_conversation_followers_conversation_id",
        table_name="cs_conversation_followers",
    )
    op.drop_index(
        "ix_cs_conversation_followers_workspace_id",
        table_name="cs_conversation_followers",
    )
    op.drop_table("cs_conversation_followers")
