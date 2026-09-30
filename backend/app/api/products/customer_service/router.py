from fastapi import APIRouter

from app.api.products.customer_service.analytics import (
    analytics_router,
    audit_logs_router,
    dashboard_router,
    reply_quality_dashboard_router,
    reply_quality_insights_router,
    reply_quality_trends_router,
)
from app.api.products.customer_service.autopilot import autopilot_router
from app.api.products.customer_service.business_value import business_value_router
from app.api.products.customer_service.automation_activity import (
    automation_activity_router,
)
from app.api.products.customer_service.automation import (
    event_subscriptions_router,
    macros_router,
    workflow_executions_router,
    workflow_templates_router,
    workflows_router,
)
from app.api.products.customer_service.channels import (
    channels_router,
    chat_router,
    omnichannel_router,
)
from app.api.products.customer_service.commercial import router as commercial_router
from app.api.products.customer_service.conversations import (
    conversation_context_router,
    conversations_router,
    tags_router,
    timeline_router,
    workspace_recommendations_router,
)
from app.api.products.customer_service.customers import (
    customers_router,
)
from app.api.products.customer_service.inbox import (
    inbox_router,
    shipping_router,
    tickets_router,
)
from app.api.products.customer_service.intelligence import (
    ai_replies_router,
    conversation_intelligence_router,
    conversation_intelligence_snapshot_router,
    quality_reviews_router,
    reply_quality_router,
    suggested_actions_router,
)
from app.api.products.customer_service.studio import studio_router
from app.api.products.customer_service.knowledge import (
    knowledge_router,
)
from app.api.products.customer_service.learning import (
    objective_learning_router,
)
from app.api.products.customer_service.email_identity import email_identity_router
from app.api.products.customer_service.helpdesk import helpdesk_router
from app.api.products.customer_service.providers.shopify import (
    shopify_router,
)
from app.api.products.customer_service.product import product_router
from app.api.products.customer_service.proactive import proactive_router
from app.api.products.customer_service.workforce import (
    agents_router,
    queues_router,
    routing_policies_router,
    sla_router,
    teams_router,
)
from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)

router = APIRouter(
    prefix="/customer-service",
)


# ------------------------------------------------------------------
# IMPORTANT:
# Preserve the exact legacy include order.
# Route precedence therefore remains unchanged.
# ------------------------------------------------------------------

router.include_router(
    inbox_router,
    prefix="/inbox",
)

router.include_router(
    conversations_router,
    prefix="/conversations",
)

router.include_router(
    customers_router,
    prefix="/customers",
)

router.include_router(
    channels_router,
    prefix="/channels",
)

router.include_router(
    workflows_router,
    prefix="/workflows",
)

router.include_router(
    analytics_router,
    prefix="/analytics",
)

router.include_router(
    dashboard_router,
)

router.include_router(
    tickets_router,
    prefix="/tickets",
)

router.include_router(
    sla_router,
)

router.include_router(
    tags_router,
)

router.include_router(
    audit_logs_router,
)

router.include_router(
    macros_router,
)

router.include_router(
    conversation_intelligence_router,
)

router.include_router(
    conversation_intelligence_snapshot_router,
)

router.include_router(
    suggested_actions_router,
)

router.include_router(
    reply_quality_router,
)

router.include_router(
    reply_quality_insights_router,
)

router.include_router(
    reply_quality_dashboard_router,
)

router.include_router(
    reply_quality_trends_router,
)

router.include_router(
    quality_reviews_router,
)

router.include_router(
    workflow_templates_router,
)

router.include_router(
    workflow_executions_router,
)

router.include_router(
    ai_replies_router,
)

router.include_router(
    knowledge_router,
)

router.include_router(
    shopify_router,
)

router.include_router(
    shipping_router,
)

router.include_router(
    omnichannel_router,
    prefix="/omnichannel",
)

router.include_router(
    event_subscriptions_router,
)

router.include_router(
    routing_policies_router,
)

router.include_router(
    agents_router,
)

router.include_router(
    teams_router,
)

router.include_router(
    queues_router,
)

router.include_router(
    chat_router,
)

router.include_router(
    timeline_router,
)

router.include_router(
    conversation_context_router,
)

router.include_router(
    workspace_recommendations_router,
)

router.include_router(
    objective_learning_router,
)

router.include_router(commercial_router)

router.include_router(product_router)

router.include_router(email_identity_router)

router.include_router(autopilot_router)
router.include_router(automation_activity_router)
router.include_router(helpdesk_router)
router.include_router(business_value_router)
router.include_router(proactive_router)


# Preserve legacy provider registration timing.
register_default_omnichannel_providers()


__all__ = ["router"]

router.include_router(
    studio_router,
    prefix="/studio",
)
