"""workflow versions

Revision ID: wv1a000000001
Revises: 61116df659df
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "wv1a000000001"
down_revision: Union[str, Sequence[str], None] = "61116df659df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("latest_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_version", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_workflow_definitions_user_id", "workflow_definitions", ["user_id"])
    op.create_index("ix_workflow_definitions_slug", "workflow_definitions", ["slug"])
    op.create_unique_constraint(
        "uq_workflow_definitions_user_slug",
        "workflow_definitions",
        ["user_id", "slug"],
    )

    op.create_table(
        "workflow_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("workflow_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evaluation_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id"],
            ["workflow_definitions.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index("ix_workflow_versions_definition_id", "workflow_versions", ["workflow_definition_id"])
    op.create_index("ix_workflow_versions_user_id", "workflow_versions", ["user_id"])
    op.create_index("ix_workflow_versions_status", "workflow_versions", ["status"])
    op.create_unique_constraint(
        "uq_workflow_versions_definition_version",
        "workflow_versions",
        ["workflow_definition_id", "version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_workflow_versions_definition_version",
        "workflow_versions",
        type_="unique",
    )
    op.drop_index("ix_workflow_versions_status", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_user_id", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_definition_id", table_name="workflow_versions")
    op.drop_table("workflow_versions")

    op.drop_constraint(
        "uq_workflow_definitions_user_slug",
        "workflow_definitions",
        type_="unique",
    )
    op.drop_index("ix_workflow_definitions_slug", table_name="workflow_definitions")
    op.drop_index("ix_workflow_definitions_user_id", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
