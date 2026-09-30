"""rename workflow runtime ids

Revision ID: c181010d4b62
Revises: 7baaa67cd8ef
Create Date: 2026-05-10 19:20:35.815850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c181010d4b62'
down_revision: Union[str, Sequence[str], None] = '7baaa67cd8ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.alter_column("workflow_runs", "run_id", new_column_name="workflow_run_id")

    op.alter_column("workflow_run_events", "run_id", new_column_name="workflow_run_id")

def downgrade() -> None:

    op.alter_column("workflow_run_events", "workflow_run_id", new_column_name="run_id")

    op.alter_column("workflow_runs", "workflow_run_id", new_column_name="run_id")
