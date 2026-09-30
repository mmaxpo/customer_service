"""add agent assist suggestions

Revision ID: 61fe64ddbf5e
Revises: 9be5177b7d07
Create Date: 2026-05-25 18:36:17.082724
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "61fe64ddbf5e"
down_revision: Union[str, Sequence[str], None] = "9be5177b7d07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


status_enum = postgresql.ENUM(
    "generated",
    "edited",
    "approved",
    "sent",
    "rejected",
    name="agentassistsuggestionstatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE agentassistsuggestionstatus AS ENUM (
                'generated',
                'edited',
                'approved',
                'sent',
                'rejected'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
    """)

    op.create_table(
        "cs_agent_assist_suggestions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("source_message_id", sa.UUID(), nullable=True),
        sa.Column("workflow_run_id", sa.UUID(), nullable=True),
        sa.Column("intent", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("original_suggestion", sa.Text(), nullable=False),
        sa.Column("current_suggestion", sa.Text(), nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="generated"),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("sent_message_id", sa.UUID(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["cs_conversations.id"], name=op.f("fk_cs_agent_assist_suggestions_conversation_id_cs_conversations")),
        sa.ForeignKeyConstraint(["source_message_id"], ["cs_conversation_messages.id"], name=op.f("fk_cs_agent_assist_suggestions_source_message_id_cs_conversation_messages")),
        sa.ForeignKeyConstraint(["sent_message_id"], ["cs_conversation_messages.id"], name=op.f("fk_cs_agent_assist_suggestions_sent_message_id_cs_conversation_messages")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cs_agent_assist_suggestions")),
    )

    op.create_index(op.f("ix_cs_agent_assist_suggestions_conversation_id"), "cs_agent_assist_suggestions", ["conversation_id"])
    op.create_index(op.f("ix_cs_agent_assist_suggestions_workflow_run_id"), "cs_agent_assist_suggestions", ["workflow_run_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_cs_agent_assist_suggestions_workflow_run_id"), table_name="cs_agent_assist_suggestions")
    op.drop_index(op.f("ix_cs_agent_assist_suggestions_conversation_id"), table_name="cs_agent_assist_suggestions")
    op.drop_table("cs_agent_assist_suggestions")
    op.execute("DROP TYPE IF EXISTS agentassistsuggestionstatus")
