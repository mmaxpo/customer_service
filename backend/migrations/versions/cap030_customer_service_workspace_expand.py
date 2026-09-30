"""Expand core customer-service rows with workspace scope.

Revision ID: cap030
Revises: cap029
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap030"
down_revision = "cap029"
branch_labels = None
depends_on = None


_TABLES = (
    "cs_customers",
    "cs_conversations",
    "cs_tickets",
)


def upgrade() -> None:
    for table_name in _TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "workspace_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            f"fk_{table_name}_workspace_id_workspaces",
            table_name,
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(
            f"ix_{table_name}_workspace_id",
            table_name,
            ["workspace_id"],
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {table_name} AS owned
                SET workspace_id = personal.id
                FROM workspaces AS personal
                WHERE personal.created_by_user_id = owned.user_id
                  AND personal.kind = 'personal'
                  AND owned.workspace_id IS NULL
                """
            )
        )


def downgrade() -> None:
    for table_name in reversed(_TABLES):
        op.drop_index(
            f"ix_{table_name}_workspace_id",
            table_name=table_name,
        )
        op.drop_constraint(
            f"fk_{table_name}_workspace_id_workspaces",
            table_name,
            type_="foreignkey",
        )
        op.drop_column(table_name, "workspace_id")
