"""Release 2 commercial customer-service foundation.

Revision ID: cap035
Revises: cap034
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap035"
down_revision = "cap034"
branch_labels = None
depends_on = None


def _id_column():
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)


def _workspace_column(*, primary_key: bool = False):
    return sa.Column(
        "workspace_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=primary_key,
        nullable=False,
    )


def _created_at():
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def upgrade() -> None:
    op.add_column(
        "cs_customers",
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("cs_customers", sa.Column("consent", postgresql.JSONB(), nullable=True))
    op.add_column(
        "cs_customers", sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_cs_customers_merged_into",
        "cs_customers",
        "cs_customers",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "cs_conversations",
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cs_conversations_merged_into",
        "cs_conversations",
        "cs_conversations",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("cs_tickets", sa.Column("resolution_reason", sa.String(100), nullable=True))
    op.add_column("cs_tickets", sa.Column("resolution_outcome", postgresql.JSONB(), nullable=True))
    op.add_column("cs_tickets", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "cs_email_webhook_receipts",
        _id_column(),
        _workspace_column(),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        _created_at(),
        sa.UniqueConstraint("provider", "event_id", name="uq_cs_email_webhook_provider_event"),
    )
    op.create_index("ix_cs_email_webhook_receipts_workspace_id", "cs_email_webhook_receipts", ["workspace_id"])

    op.create_table(
        "cs_saved_views",
        _id_column(),
        _workspace_column(),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created_at(),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "name", name="uq_cs_saved_view_workspace_name"),
    )
    op.create_index("ix_cs_saved_views_workspace_id", "cs_saved_views", ["workspace_id"])

    op.create_table(
        "cs_attachments",
        _id_column(),
        _workspace_column(),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_conversation_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("scan_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("scan_detail", sa.String(500), nullable=True),
        _created_at(),
    )
    op.create_index("ix_cs_attachments_workspace_id", "cs_attachments", ["workspace_id"])
    op.create_index("ix_cs_attachments_conversation_id", "cs_attachments", ["conversation_id"])
    op.create_index("ix_cs_attachments_workspace_conversation", "cs_attachments", ["workspace_id", "conversation_id"])

    op.create_table(
        "cs_conversation_edit_leases",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_conversations.id", ondelete="CASCADE"), primary_key=True),
        _workspace_column(),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lease_token", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cs_conversation_edit_leases_workspace_id", "cs_conversation_edit_leases", ["workspace_id"])
    op.create_index("ix_cs_conversation_edit_leases_actor_user_id", "cs_conversation_edit_leases", ["actor_user_id"])
    op.create_index("ix_cs_conversation_edit_leases_expires_at", "cs_conversation_edit_leases", ["expires_at"])

    op.create_table(
        "cs_notifications",
        _id_column(),
        _workspace_column(),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
    )
    op.create_index("ix_cs_notifications_workspace_id", "cs_notifications", ["workspace_id"])
    op.create_index("ix_cs_notifications_recipient_user_id", "cs_notifications", ["recipient_user_id"])
    op.create_index("ix_cs_notifications_kind", "cs_notifications", ["kind"])
    op.create_index("ix_cs_notifications_recipient_unread", "cs_notifications", ["recipient_user_id", "read_at"])

    op.create_table(
        "cs_sla_calendars",
        _id_column(),
        _workspace_column(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("weekly_hours", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("holidays", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("escalation_policy", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created_at(),
        sa.UniqueConstraint("workspace_id", "name", name="uq_cs_sla_calendar_workspace_name"),
    )
    op.create_index("ix_cs_sla_calendars_workspace_id", "cs_sla_calendars", ["workspace_id"])

    op.create_table(
        "cs_merge_events",
        _id_column(),
        _workspace_column(),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        _created_at(),
    )
    op.create_index("ix_cs_merge_events_workspace_id", "cs_merge_events", ["workspace_id"])

    op.create_table(
        "cs_csat_surveys",
        _id_column(),
        _workspace_column(),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        sa.CheckConstraint("score IS NULL OR (score >= 1 AND score <= 5)", name="ck_cs_csat_score_range"),
    )
    op.create_index("ix_cs_csat_surveys_workspace_id", "cs_csat_surveys", ["workspace_id"])
    op.create_index("ix_cs_csat_surveys_conversation_id", "cs_csat_surveys", ["conversation_id"])

    op.create_table(
        "cs_onboarding_states",
        _workspace_column(primary_key=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("checklist", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("demo_data_seeded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "workspace_subscriptions",
        _workspace_column(primary_key=True),
        sa.Column("plan", sa.String(32), nullable=False, server_default="trial"),
        sa.Column("status", sa.String(32), nullable=False, server_default="trialing"),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("provider_customer_id", sa.String(255), nullable=True, unique=True),
        sa.Column("provider_subscription_id", sa.String(255), nullable=True, unique=True),
        sa.Column("entitlements", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cs_privacy_requests",
        _id_column(),
        _workspace_column(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("result", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error", sa.Text(), nullable=True),
        _created_at(),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cs_privacy_requests_workspace_id", "cs_privacy_requests", ["workspace_id"])


def downgrade() -> None:
    for table in (
        "cs_privacy_requests",
        "workspace_subscriptions",
        "cs_onboarding_states",
        "cs_csat_surveys",
        "cs_merge_events",
        "cs_sla_calendars",
        "cs_notifications",
        "cs_conversation_edit_leases",
        "cs_attachments",
        "cs_saved_views",
        "cs_email_webhook_receipts",
    ):
        op.drop_table(table)
    op.drop_column("cs_tickets", "resolved_at")
    op.drop_column("cs_tickets", "resolution_outcome")
    op.drop_column("cs_tickets", "resolution_reason")
    op.drop_constraint("fk_cs_conversations_merged_into", "cs_conversations", type_="foreignkey")
    op.drop_column("cs_conversations", "merged_into_id")
    op.drop_constraint("fk_cs_customers_merged_into", "cs_customers", type_="foreignkey")
    op.drop_column("cs_customers", "anonymized_at")
    op.drop_column("cs_customers", "consent")
    op.drop_column("cs_customers", "merged_into_id")
