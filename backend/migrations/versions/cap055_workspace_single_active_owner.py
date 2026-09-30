"""enforce one active workspace owner

Revision ID: cap055
Revises: cap054
"""

from alembic import op
import sqlalchemy as sa


revision = "cap055"
down_revision = "cap054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Refuse to guess if pre-existing data violates the invariant.
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            "SELECT workspace_id FROM workspace_memberships "
            "WHERE role = 'owner' AND status = 'active' "
            "GROUP BY workspace_id HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError(
            "cannot add active-owner uniqueness guard; duplicate owners exist for "
            + ", ".join(str(row[0]) for row in duplicates)
        )
    op.create_index(
        "uq_workspace_memberships_active_owner",
        "workspace_memberships",
        ["workspace_id"],
        unique=True,
        postgresql_where=sa.text("role = 'owner' AND status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_workspace_memberships_active_owner",
        table_name="workspace_memberships",
    )
