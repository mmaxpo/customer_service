"""
Customer-service ORM model public API.

Import models from this package instead of depending on individual physical
model files. This keeps future file layout changes safe.
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
    CustomerIdentity,
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
    CustomerServiceAgentTimeOff,
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
from app.domains.customer_service.models.commercial import (
    ConversationFollower,
    ConversationEditLease,
    CustomerServiceAttachment,
    CustomerServiceCSATSurvey,
    CustomerServiceMergeEvent,
    CustomerServiceNotification,
    CustomerServiceOnboardingState,
    CustomerServicePrivacyRequest,
    CustomerServiceSavedView,
    CustomerServiceReplyDraft,
    CustomerServiceReplySignature,
    CustomerServiceSLACalendar,
    EmailWebhookReceipt,
    WorkspaceSubscription,
)
from app.domains.customer_service.models.management import (
    CustomerServiceEmailIdentity,
    CustomerServiceKnowledgeEvaluationQuestion,
    CustomerServiceKnowledgeSettings,
    CustomerServiceKnowledgeSource,
)
from app.domains.customer_service.models.product_control import (
    CustomerServiceAutopilotPolicy,
    CustomerServiceProactiveIncident,
    CustomerServiceProactivePolicy,
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
    "CustomerIdentity",
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
    "CustomerServiceAgentTimeOff",
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
    "ConversationFollower",
    "ConversationEditLease",
    "CustomerServiceAttachment",
    "CustomerServiceCSATSurvey",
    "CustomerServiceMergeEvent",
    "CustomerServiceNotification",
    "CustomerServiceOnboardingState",
    "CustomerServicePrivacyRequest",
    "CustomerServiceSavedView",
    "CustomerServiceReplyDraft",
    "CustomerServiceReplySignature",
    "CustomerServiceSLACalendar",
    "EmailWebhookReceipt",
    "WorkspaceSubscription",
    "CustomerServiceEmailIdentity",
    "CustomerServiceKnowledgeSource",
    "CustomerServiceKnowledgeSettings",
    "CustomerServiceKnowledgeEvaluationQuestion",
    "CustomerServiceAutopilotPolicy",
    "CustomerServiceProactivePolicy",
    "CustomerServiceProactiveIncident",
]
