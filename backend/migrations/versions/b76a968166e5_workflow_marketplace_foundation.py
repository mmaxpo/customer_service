"""workflow marketplace foundation

Revision ID: b76a968166e5
Revises: 7391df9a2134
Create Date: 2026-05-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b76a968166e5"
down_revision: Union[str, Sequence[str], None] = "7391df9a2134"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.String(length=50), nullable=False, server_default="system"),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workflow_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.String(length=20), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_cs_workflow_templates_user_id", "cs_workflow_templates", ["user_id"])
    op.create_index("ix_cs_workflow_templates_scope", "cs_workflow_templates", ["scope"])
    op.create_index("ix_cs_workflow_templates_category", "cs_workflow_templates", ["category"])


def downgrade() -> None:
    op.drop_index("ix_cs_workflow_templates_category", table_name="cs_workflow_templates")
    op.drop_index("ix_cs_workflow_templates_scope", table_name="cs_workflow_templates")
    op.drop_index("ix_cs_workflow_templates_user_id", table_name="cs_workflow_templates")
    op.drop_table("cs_workflow_templates")