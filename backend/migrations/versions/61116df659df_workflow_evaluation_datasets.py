"""workflow evaluation datasets

Revision ID: 61116df659df
Revises: ws1a000000001
Create Date: 2026-05-28 11:34:52.682917
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "61116df659df"
down_revision: Union[str, Sequence[str], None] = "ws1a000000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_eval_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_workflow_eval_datasets_user_id",
        "workflow_eval_datasets",
        ["user_id"],
    )
    op.create_index(
        "ix_workflow_eval_datasets_domain",
        "workflow_eval_datasets",
        ["domain"],
    )

    op.create_table(
        "workflow_eval_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "expected_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("expected_status", sa.String(length=100), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["workflow_eval_datasets.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_workflow_eval_cases_dataset_id",
        "workflow_eval_cases",
        ["dataset_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_eval_cases_dataset_id",
        table_name="workflow_eval_cases",
    )
    op.drop_table("workflow_eval_cases")

    op.drop_index(
        "ix_workflow_eval_datasets_domain",
        table_name="workflow_eval_datasets",
    )
    op.drop_index(
        "ix_workflow_eval_datasets_user_id",
        table_name="workflow_eval_datasets",
    )
    op.drop_table("workflow_eval_datasets")
