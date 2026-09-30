"""add customer chat inbox links

Revision ID: 9f6e8c12b4a1
Revises: 4d1058d87f45
Create Date: 2026-06-09 19:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f6e8c12b4a1"
down_revision: Union[str, Sequence[str], None] = "4d1058d87f45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cs_chat_inbox_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("chat_session_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("ticket_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["chat_session_id"],
            ["cs_chat_sessions.id"],
            name=op.f("fk_cs_chat_inbox_links_chat_session_id_cs_chat_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["cs_customers.id"],
            name=op.f("fk_cs_chat_inbox_links_customer_id_cs_customers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["cs_conversations.id"],
            name=op.f("fk_cs_chat_inbox_links_conversation_id_cs_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["cs_tickets.id"],
            name=op.f("fk_cs_chat_inbox_links_ticket_id_cs_tickets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cs_chat_inbox_links")),
    )

    op.create_index(
        op.f("ix_cs_chat_inbox_links_user_id"),
        "cs_chat_inbox_links",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cs_chat_inbox_links_chat_session_id"),
        "cs_chat_inbox_links",
        ["chat_session_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_cs_chat_inbox_links_customer_id"),
        "cs_chat_inbox_links",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cs_chat_inbox_links_conversation_id"),
        "cs_chat_inbox_links",
        ["conversation_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_cs_chat_inbox_links_ticket_id"),
        "cs_chat_inbox_links",
        ["ticket_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cs_chat_inbox_links_ticket_id"), table_name="cs_chat_inbox_links")
    op.drop_index(op.f("ix_cs_chat_inbox_links_conversation_id"), table_name="cs_chat_inbox_links")
    op.drop_index(op.f("ix_cs_chat_inbox_links_customer_id"), table_name="cs_chat_inbox_links")
    op.drop_index(op.f("ix_cs_chat_inbox_links_chat_session_id"), table_name="cs_chat_inbox_links")
    op.drop_index(op.f("ix_cs_chat_inbox_links_user_id"), table_name="cs_chat_inbox_links")
    op.drop_table("cs_chat_inbox_links")
