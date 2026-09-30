"""workflow deployments

Revision ID: wd1a000000001
Revises: wm1a000000001
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "wd1a000000001"
down_revision: Union[str, Sequence[str], None] = "wm1a000000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow_key", sa.String(), nullable=False),
        sa.Column("workflow_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("environment", sa.String(), nullable=False),
        sa.Column("deployed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_workflow_deployments_workflow_key",
        "workflow_deployments",
        ["workflow_key"],
    )
    op.create_index(
        "ix_workflow_deployments_workflow_version_id",
        "workflow_deployments",
        ["workflow_version_id"],
    )
    op.create_index(
        "ix_workflow_deployments_environment",
        "workflow_deployments",
        ["environment"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_deployments_environment",
        table_name="workflow_deployments",
    )
    op.drop_index(
        "ix_workflow_deployments_workflow_version_id",
        table_name="workflow_deployments",
    )
    op.drop_index(
        "ix_workflow_deployments_workflow_key",
        table_name="workflow_deployments",
    )
    op.drop_table("workflow_deployments")
