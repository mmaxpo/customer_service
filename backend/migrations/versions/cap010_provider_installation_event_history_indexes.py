"""add provider installation event history indexes

Revision ID: cap010
Revises: cap009
Create Date: 2026-07-18
"""

from alembic import op


revision = "cap010"
down_revision = "cap009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX
        IF NOT EXISTS
        ix_platform_events_user_source_created
        ON platform_events (
            user_id,
            source,
            created_at DESC
        )
        """
    )

    op.execute(
        """
        CREATE INDEX
        IF NOT EXISTS
        ix_platform_events_provider_installation_history
        ON platform_events (
            user_id,
            (payload ->> 'provider_id'),
            event_type,
            created_at DESC
        )
        WHERE source =
            'runtime.provider_installations'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS
        ix_platform_events_provider_installation_history
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS
        ix_platform_events_user_source_created
        """
    )
