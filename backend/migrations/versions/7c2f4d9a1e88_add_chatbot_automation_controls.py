"""add chatbot automation controls

Revision ID: 7c2f4d9a1e88
Revises: 9f6e8c12b4a1
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c2f4d9a1e88"
down_revision: Union[str, Sequence[str], None] = "9f6e8c12b4a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cs_chat_widget_settings",
        sa.Column(
            "auto_answer_confidence_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.75",
        ),
    )
    op.add_column(
        "cs_chat_widget_settings",
        sa.Column(
            "human_handoff_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "cs_chat_widget_settings",
        sa.Column(
            "human_handoff_message",
            sa.Text(),
            nullable=False,
            server_default="I’ll connect you with our support team now.",
        ),
    )


def downgrade() -> None:
    op.drop_column("cs_chat_widget_settings", "human_handoff_message")
    op.drop_column("cs_chat_widget_settings", "human_handoff_enabled")
    op.drop_column("cs_chat_widget_settings", "auto_answer_confidence_threshold")
