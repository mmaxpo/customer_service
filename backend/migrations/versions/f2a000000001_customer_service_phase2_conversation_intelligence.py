"""customer service phase2 conversation intelligence

Revision ID: f2a000000001
Revises: f1b000000001
Create Date: 2026-05-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f2a000000001"
down_revision: Union[str, Sequence[str], None] = "f1b000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_conversation_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sentiment", sa.String(length=50), nullable=False),
        sa.Column("intent", sa.String(length=100), nullable=False),
        sa.Column("urgency", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("opportunities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="rule"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["cs_conversations.id"]),
    )

    op.create_index("ix_cs_conversation_insights_user_id", "cs_conversation_insights", ["user_id"])
    op.create_index("ix_cs_conversation_insights_conversation_id", "cs_conversation_insights", ["conversation_id"])
    op.create_index("ix_cs_conversation_insights_sentiment", "cs_conversation_insights", ["sentiment"])
    op.create_index("ix_cs_conversation_insights_intent", "cs_conversation_insights", ["intent"])
    op.create_index("ix_cs_conversation_insights_urgency", "cs_conversation_insights", ["urgency"])


def downgrade() -> None:
    op.drop_index("ix_cs_conversation_insights_urgency", table_name="cs_conversation_insights")
    op.drop_index("ix_cs_conversation_insights_intent", table_name="cs_conversation_insights")
    op.drop_index("ix_cs_conversation_insights_sentiment", table_name="cs_conversation_insights")
    op.drop_index("ix_cs_conversation_insights_conversation_id", table_name="cs_conversation_insights")
    op.drop_index("ix_cs_conversation_insights_user_id", table_name="cs_conversation_insights")
    op.drop_table("cs_conversation_insights")
