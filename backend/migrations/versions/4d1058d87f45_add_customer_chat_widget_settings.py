"""add customer chat widget settings

Revision ID: 4d1058d87f45
Revises: eccd20e35ed0
Create Date: 2026-06-09 18:28:04.081258
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "4d1058d87f45"
down_revision: Union[str, Sequence[str], None] = "eccd20e35ed0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cs_chat_widget_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("public_key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("title", sa.String(length=120), nullable=False, server_default="Chat with us"),
        sa.Column(
            "welcome_message",
            sa.Text(),
            nullable=False,
            server_default="Hi! How can we help you today?",
        ),
        sa.Column("brand_color", sa.String(length=32), nullable=False, server_default="#16a34a"),
        sa.Column("position", sa.String(length=32), nullable=False, server_default="bottom-right"),
        sa.Column("assistant_name", sa.String(length=120), nullable=False, server_default="Tajeran AI"),
        sa.Column("auto_answer_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("workflow_template_id", sa.UUID(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cs_chat_widget_settings")),
    )
    op.create_index(
        op.f("ix_cs_chat_widget_settings_public_key"),
        "cs_chat_widget_settings",
        ["public_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_cs_chat_widget_settings_user_id"),
        "cs_chat_widget_settings",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cs_chat_widget_settings_user_id"), table_name="cs_chat_widget_settings")
    op.drop_index(op.f("ix_cs_chat_widget_settings_public_key"), table_name="cs_chat_widget_settings")
    op.drop_table("cs_chat_widget_settings")
