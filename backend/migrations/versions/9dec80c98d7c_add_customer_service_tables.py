"""add customer service tables

Revision ID: 9dec80c98d7c
Revises: c181010d4b62
Create Date: 2026-05-24 14:08:48.553703
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "9dec80c98d7c"
down_revision: Union[str, Sequence[str], None] = "c181010d4b62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "cs_customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "BLOCKED", name="customerstatus"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cs_customers")),
    )

    op.create_index(
        op.f("ix_cs_customers_email"),
        "cs_customers",
        ["email"],
        unique=False,
    )

    op.create_index(
        op.f("ix_cs_customers_user_id"),
        "cs_customers",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "cs_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "PENDING",
                "RESOLVED",
                name="conversationstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["cs_customers.id"],
            name=op.f(
                "fk_cs_conversations_customer_id_cs_customers"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_cs_conversations"),
        ),
    )

    op.create_index(
        op.f("ix_cs_conversations_customer_id"),
        "cs_conversations",
        ["customer_id"],
    )

    op.create_index(
        op.f("ix_cs_conversations_user_id"),
        "cs_conversations",
        ["user_id"],
    )

    op.create_table(
        "cs_conversation_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column(
            "sender_type",
            sa.Enum(
                "CUSTOMER",
                "AGENT",
                "AI",
                "SYSTEM",
                name="messagesendertype",
            ),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["cs_conversations.id"],
            name=op.f(
                "fk_cs_conversation_messages_conversation_id_cs_conversations"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_cs_conversation_messages"),
        ),
    )

    op.create_index(
        op.f("ix_cs_conversation_messages_conversation_id"),
        "cs_conversation_messages",
        ["conversation_id"],
    )

    op.create_table(
        "cs_tickets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "PENDING",
                "RESOLVED",
                "CLOSED",
                name="ticketstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "LOW",
                "NORMAL",
                "HIGH",
                "URGENT",
                name="ticketpriority",
            ),
            nullable=False,
        ),
        sa.Column(
            "assigned_to",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["cs_conversations.id"],
            name=op.f(
                "fk_cs_tickets_conversation_id_cs_conversations"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_cs_tickets"),
        ),
    )

    op.create_index(
        op.f("ix_cs_tickets_conversation_id"),
        "cs_tickets",
        ["conversation_id"],
    )

    op.create_index(
        op.f("ix_cs_tickets_user_id"),
        "cs_tickets",
        ["user_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_cs_tickets_user_id"),
        table_name="cs_tickets",
    )

    op.drop_index(
        op.f("ix_cs_tickets_conversation_id"),
        table_name="cs_tickets",
    )

    op.drop_table("cs_tickets")

    op.drop_index(
        op.f("ix_cs_conversation_messages_conversation_id"),
        table_name="cs_conversation_messages",
    )

    op.drop_table("cs_conversation_messages")

    op.drop_index(
        op.f("ix_cs_conversations_user_id"),
        table_name="cs_conversations",
    )

    op.drop_index(
        op.f("ix_cs_conversations_customer_id"),
        table_name="cs_conversations",
    )

    op.drop_table("cs_conversations")

    op.drop_index(
        op.f("ix_cs_customers_user_id"),
        table_name="cs_customers",
    )

    op.drop_index(
        op.f("ix_cs_customers_email"),
        table_name="cs_customers",
    )

    op.drop_table("cs_customers")