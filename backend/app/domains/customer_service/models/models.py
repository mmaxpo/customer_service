"""
Compatibility re-exports for customer-service ORM models.

New code should import from `app.domains.customer_service.models`.
The concrete model definitions live in focused modules in this package.
"""

from app.domains.customer_service.models.enums import (
    AgentAssistSuggestionStatus,
    ConversationStatus,
    CustomerStatus,
    MessageSenderType,
    SLATargetType,
    SLAViolationStatus,
    TicketPriority,
    TicketStatus,
)
from app.domains.customer_service.models.core import (
    Customer,
    Conversation,
    ConversationMessage,
)
from app.domains.customer_service.models.chat import (
    CustomerChatWidgetSettings,
    CustomerChatSession,
    CustomerChatInboxLink,
    CustomerChatMessage,
)
from app.domains.customer_service.models.tickets import (
    Ticket,
    TicketAssignment,
    ConversationTag,
    CustomerServiceAuditLog,
    CustomerServiceMacro,
)
from app.domains.customer_service.models.sla import (
    SLAPolicy,
    SLAViolation,
)
from app.domains.customer_service.models.routing import (
    CustomerServiceRoutingPolicy,
    CustomerServiceAgent,
    CustomerServiceTeam,
    CustomerServiceQueue,
    CustomerServiceTeamMember,
)
from app.domains.customer_service.models.shopify import (
    CustomerServiceShopifyConnection,
    CustomerServiceShopifyOrderCache,
    CustomerServiceShippingTrackingCache,
    ShopifyOAuthInstallSession,
    ShopifyWebhookReceipt,
)
from app.domains.customer_service.models.omnichannel import (
    CustomerServiceChannelConnection,
    CustomerServiceExternalConversationLink,
    CustomerServiceExternalMessageLink,
    CustomerServiceExternalMediaLink,
    CustomerServiceEventSubscription,
)
from app.domains.customer_service.models.quality import (
    AgentAssistSuggestion,
    AgentAssistSuggestionRevision,
    CustomerServiceConversationInsight,
    CustomerServiceSuggestedAction,
    CustomerServiceQualityReview,
)
from app.domains.customer_service.models.workflows import (
    CustomerServiceWorkflowTemplate,
)
from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeEvaluationRecord,
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.models.management import (
    CustomerServiceEmailIdentity,
    CustomerServiceKnowledgeEvaluationQuestion,
    CustomerServiceKnowledgeSettings,
    CustomerServiceKnowledgeSource,
)

__all__ = [
    "CustomerStatus",
    "ConversationStatus",
    "TicketStatus",
    "TicketPriority",
    "MessageSenderType",
    "AgentAssistSuggestionStatus",
    "SLATargetType",
    "SLAViolationStatus",
    "Customer",
    "Conversation",
    "ConversationMessage",
    "CustomerChatWidgetSettings",
    "CustomerChatSession",
    "CustomerChatInboxLink",
    "CustomerChatMessage",
    "Ticket",
    "TicketAssignment",
    "ConversationTag",
    "CustomerServiceAuditLog",
    "CustomerServiceMacro",
    "SLAPolicy",
    "SLAViolation",
    "CustomerServiceRoutingPolicy",
    "CustomerServiceAgent",
    "CustomerServiceTeam",
    "CustomerServiceQueue",
    "CustomerServiceTeamMember",
    "CustomerServiceShopifyConnection",
    "CustomerServiceShopifyOrderCache",
    "CustomerServiceShippingTrackingCache",
    "ShopifyOAuthInstallSession",
    "ShopifyWebhookReceipt",
    "CustomerServiceChannelConnection",
    "CustomerServiceExternalConversationLink",
    "CustomerServiceExternalMessageLink",
    "CustomerServiceExternalMediaLink",
    "CustomerServiceEventSubscription",
    "AgentAssistSuggestion",
    "AgentAssistSuggestionRevision",
    "CustomerServiceConversationInsight",
    "CustomerServiceSuggestedAction",
    "CustomerServiceQualityReview",
    "CustomerServiceWorkflowTemplate",
    "CustomerSupportOutcomeRecord",
    "CustomerSupportOutcomeEvaluationRecord",
    "CustomerServiceEmailIdentity",
    "CustomerServiceKnowledgeSource",
    "CustomerServiceKnowledgeSettings",
    "CustomerServiceKnowledgeEvaluationQuestion",
]
