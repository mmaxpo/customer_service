"""Scope platform-job idempotency by user.

Revision ID: cap027
Revises: cap026
"""

from alembic import op
import sqlalchemy as sa


revision = "cap027"
down_revision = "cap026"
branch_labels = None
depends_on = None


OLD_INDEX = "uq_platform_jobs_type_idempotency_key"

TENANT_INDEX = "uq_platform_jobs_user_type_idempotency_key"

GLOBAL_INDEX = "uq_platform_jobs_global_type_idempotency_key"


def upgrade() -> None:
    op.drop_index(
        OLD_INDEX,
        table_name="platform_jobs",
    )

    op.create_index(
        TENANT_INDEX,
        "platform_jobs",
        [
            "user_id",
            "job_type",
            "idempotency_key",
        ],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL AND idempotency_key IS NOT NULL"),
    )

    op.create_index(
        GLOBAL_INDEX,
        "platform_jobs",
        [
            "job_type",
            "idempotency_key",
        ],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL AND idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        GLOBAL_INDEX,
        table_name="platform_jobs",
    )

    op.drop_index(
        TENANT_INDEX,
        table_name="platform_jobs",
    )

    # Recreating the historical global index can fail if the
    # database contains different users with the same
    # (job_type, idempotency_key). That is expected: the old
    # schema cannot represent tenant-isolated idempotency.
    op.create_index(
        OLD_INDEX,
        "platform_jobs",
        [
            "job_type",
            "idempotency_key",
        ],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
