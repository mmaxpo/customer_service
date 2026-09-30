"""Cut customer-service tenant keys over to workspace IDs.

Revision ID: cap034
Revises: cap033

Legacy rows whose user ID has no corresponding account/workspace are retained
for test/dev compatibility. All real-account rows and all new HTTP writes use
the workspace UUID as the legacy ``user_id`` tenant key.
"""

from alembic import op


revision = "cap034"
down_revision = "cap033"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "cs_agents",
    "cs_audit_logs",
    "cs_channel_connections",
    "cs_chat_inbox_links",
    "cs_chat_sessions",
    "cs_chat_widget_settings",
    "cs_conversation_insights",
    "cs_conversation_tags",
    "cs_conversations",
    "cs_customers",
    "cs_event_subscriptions",
    "cs_external_conversation_links",
    "cs_external_message_links",
    "cs_macros",
    "cs_quality_reviews",
    "cs_queues",
    "cs_routing_policies",
    "cs_shipping_tracking_cache",
    "cs_shopify_connections",
    "cs_shopify_order_cache",
    "cs_sla_policies",
    "cs_sla_violations",
    "cs_suggested_actions",
    "cs_support_outcome_evaluations",
    "cs_support_outcomes",
    "cs_team_members",
    "cs_teams",
    "cs_ticket_assignments",
    "cs_tickets",
    "cs_workflow_templates",
)


def upgrade() -> None:
    for table_name in TENANT_TABLES:
        op.execute(
            f"""
            UPDATE {table_name} AS tenant_row
            SET user_id = workspace.id
            FROM workspaces AS workspace
            WHERE workspace.created_by_user_id = tenant_row.user_id
              AND workspace.kind = 'personal'
            """
        )

    for table_name in ("cs_customers", "cs_conversations", "cs_tickets"):
        op.execute(
            f"""
            UPDATE {table_name}
            SET workspace_id = user_id
            WHERE workspace_id IS NULL
              AND EXISTS (
                  SELECT 1 FROM workspaces
                  WHERE workspaces.id = {table_name}.user_id
              )
            """
        )


def downgrade() -> None:
    raise RuntimeError(
        "cap034 is a forward-only tenant ownership cutover; restore from the "
        "pre-release backup instead of attempting an in-place downgrade"
    )
