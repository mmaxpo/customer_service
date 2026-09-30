"""add agent assist suggestion revisions

Revision ID: b046ed1ffd7c
Revises: 61fe64ddbf5e
Create Date: 2026-05-25 20:50:34.149583
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b046ed1ffd7c"
down_revision: Union[str, Sequence[str], None] = "61fe64ddbf5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cs_agent_assist_suggestion_revisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("suggestion_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("edited_by", sa.UUID(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["suggestion_id"],
            ["cs_agent_assist_suggestions.id"],
            name=op.f(
                "fk_cs_agent_assist_suggestion_revisions_suggestion_id_cs_agent_assist_suggestions"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_cs_agent_assist_suggestion_revisions"),
        ),
    )

    op.create_index(
        op.f("ix_cs_agent_assist_suggestion_revisions_suggestion_id"),
        "cs_agent_assist_suggestion_revisions",
        ["suggestion_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_cs_agent_assist_suggestion_revisions_suggestion_id"),
        table_name="cs_agent_assist_suggestion_revisions",
    )
    op.drop_table("cs_agent_assist_suggestion_revisions")
