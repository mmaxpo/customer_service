"""add_customer_chat_models

Revision ID: eccd20e35ed0
Revises: qr1a000000001
Create Date: 2026-06-09 11:09:14.924549
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "eccd20e35ed0"
down_revision: Union[str, Sequence[str], None] = "qr1a000000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cs_chat_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("visitor_id", sa.String(length=255), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cs_chat_sessions")),
    )

    op.create_index(op.f("ix_cs_chat_sessions_channel"), "cs_chat_sessions", ["channel"], unique=False)
    op.create_index(op.f("ix_cs_chat_sessions_customer_email"), "cs_chat_sessions", ["customer_email"], unique=False)
    op.create_index(op.f("ix_cs_chat_sessions_status"), "cs_chat_sessions", ["status"], unique=False)
    op.create_index(op.f("ix_cs_chat_sessions_user_id"), "cs_chat_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_cs_chat_sessions_visitor_id"), "cs_chat_sessions", ["visitor_id"], unique=False)

    op.create_table(
        "cs_chat_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["cs_chat_sessions.id"],
            name=op.f("fk_cs_chat_messages_session_id_cs_chat_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cs_chat_messages")),
    )

    op.create_index(op.f("ix_cs_chat_messages_role"), "cs_chat_messages", ["role"], unique=False)
    op.create_index(op.f("ix_cs_chat_messages_session_id"), "cs_chat_messages", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cs_chat_messages_session_id"), table_name="cs_chat_messages")
    op.drop_index(op.f("ix_cs_chat_messages_role"), table_name="cs_chat_messages")
    op.drop_table("cs_chat_messages")

    op.drop_index(op.f("ix_cs_chat_sessions_visitor_id"), table_name="cs_chat_sessions")
    op.drop_index(op.f("ix_cs_chat_sessions_user_id"), table_name="cs_chat_sessions")
    op.drop_index(op.f("ix_cs_chat_sessions_status"), table_name="cs_chat_sessions")
    op.drop_index(op.f("ix_cs_chat_sessions_customer_email"), table_name="cs_chat_sessions")
    op.drop_index(op.f("ix_cs_chat_sessions_channel"), table_name="cs_chat_sessions")
    op.drop_table("cs_chat_sessions")
