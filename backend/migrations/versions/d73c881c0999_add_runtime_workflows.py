"""add_runtime_workflows

Revision ID: d73c881c0999
Revises: 4f2b7c945184
Create Date: 2026-02-19 18:03:30.647521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd73c881c0999'
down_revision: Union[str, Sequence[str], None] = '4f2b7c945184'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runtime_workflows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("workflow", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runtime_workflows_user_id"), "runtime_workflows", ["user_id"], unique=False)
    op.create_index("ix_runtime_workflows_user_id_name", "runtime_workflows", ["user_id", "name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_runtime_workflows_user_id_name", table_name="runtime_workflows")
    op.drop_index(op.f("ix_runtime_workflows_user_id"), table_name="runtime_workflows")
    op.drop_table("runtime_workflows")
