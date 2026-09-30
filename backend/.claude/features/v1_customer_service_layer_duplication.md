# customer_service layer duplication audit
_generated 2026-09-21T18:23:33_

domains/customer_service: 283 files
api/products/customer_service: 22 files

## Filename overlaps between the two trees: 15

### __init__.py
- **domains**: `app/domains/customer_service/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/chat/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/devtools/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/events/__init__.py` (1 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/inbox/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/inbox/providers/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/integrations/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/integrations/omnichannel/__init__.py` (1 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/integrations/shopify/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/jobs/__init__.py` (1 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/models/__init__.py` (172 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models.enums import AgentAssistSuggestionStatus, ConversationStatus, CustomerStatus, MessageSenderType, SLATargetType, SLAViolationStatus, TicketPriority, TicketStatus', 'from app.domains.customer_service.models.core import Customer, CustomerIdentity, Conversation, ConversationMessage', 'from app.domains.customer_service.models.chat import CustomerChatWidgetSettings, CustomerChatSession, CustomerChatInboxLink, CustomerChatMessage', 'from app.domains.customer_service.models.tickets import Ticket, TicketAssignment, ConversationTag, CustomerServiceAuditLog, CustomerServiceMacro', 'from app.domains.customer_service.models.sla import SLAPolicy, SLAViolation', 'from app.domains.customer_service.models.routing import CustomerServiceRoutingPolicy, CustomerServiceAgent, CustomerServiceTeam, CustomerServiceQueue, CustomerServiceTeamMember', 'from app.domains.customer_service.models.shopify import CustomerServiceShopifyConnection, CustomerServiceShopifyOrderCache, CustomerServiceShippingTrackingCache, ShopifyOAuthInstallSession, ShopifyWebhookReceipt', 'from app.domains.customer_service.models.omnichannel import CustomerServiceChannelConnection, CustomerServiceExternalConversationLink, CustomerServiceExternalMessageLink, CustomerServiceExternalMediaLink, CustomerServiceEventSubscription', 'from app.domains.customer_service.models.quality import AgentAssistSuggestion, AgentAssistSuggestionRevision, CustomerServiceConversationInsight, CustomerServiceSuggestedAction, CustomerServiceQualityReview', 'from app.domains.customer_service.models.workflows import CustomerServiceWorkflowTemplate', 'from app.domains.customer_service.models.outcomes import CustomerSupportOutcomeEvaluationRecord, CustomerSupportOutcomeRecord', 'from app.domains.customer_service.models.commercial import ConversationFollower, ConversationEditLease, CustomerServiceAttachment, CustomerServiceCSATSurvey, CustomerServiceMergeEvent, CustomerServiceNotification, CustomerServiceOnboardingState, CustomerServicePrivacyRequest, CustomerServiceSavedView, CustomerServiceReplyDraft, CustomerServiceReplySignature, CustomerServiceSLACalendar, EmailWebhookReceipt, WorkspaceSubscription', 'from app.domains.customer_service.models.management import CustomerServiceEmailIdentity, CustomerServiceKnowledgeEvaluationQuestion, CustomerServiceKnowledgeSettings, CustomerServiceKnowledgeSource', 'from app.domains.customer_service.models.product_control import CustomerServiceAutopilotPolicy, CustomerServiceProactiveIncident, CustomerServiceProactivePolicy']
- **domains**: `app/domains/customer_service/realtime/__init__.py` (5 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.realtime.publisher import CustomerServiceRealtimePublisher']
- **domains**: `app/domains/customer_service/repositories/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/runtime/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/runtime/nodes/__init__.py` (9 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/schemas/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/security/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/routing_engine/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/support/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/support/commerce/__init__.py` (1 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/support/learning/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/support/objective/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/support/outcome/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/support/planning/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/support/repair/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/support/resolution/__init__.py` (0 lines)
  - classes: []
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/workforce/__init__.py` (1 lines)
  - classes: []
  - top-level functions: []
- **api**: `app/api/products/customer_service/__init__.py` (5 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.api.products.customer_service.router import router']
- **api**: `app/api/products/customer_service/providers/__init__.py` (1 lines)
  - classes: []
  - top-level functions: []

### analytics.py
- **domains**: `app/domains/customer_service/repositories/analytics.py` (191 lines)
  - classes: ['AnalyticsRepository']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import Customer, Conversation, Ticket, TicketAssignment, SLAViolation, SLAViolationStatus, CustomerServiceQueue, CustomerServiceTeam, CustomerServiceTeamMember, CustomerServiceAgent']
- **domains**: `app/domains/customer_service/schemas/analytics.py` (16 lines)
  - classes: ['CustomerServiceAnalytics', 'WorkloadReportItem']
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/analytics.py` (34 lines)
  - classes: ['AnalyticsService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.repositories.analytics import AnalyticsRepository']
- **api**: `app/api/products/customer_service/analytics.py` (549 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.schemas.analytics import CustomerServiceAnalytics, WorkloadReportItem', 'from app.domains.customer_service.schemas.workload import WorkloadReport', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.analytics import AnalyticsService', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.dashboard import CustomerServiceDashboardService', 'from app.domains.customer_service.schemas.reply_quality_insights import ReplyQualityInsightsRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.reply_quality_insights import ReplyQualityInsightsService', 'from app.domains.customer_service.schemas.reply_quality_dashboard import ReplyQualityDashboardRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.reply_quality_dashboard import ReplyQualityDashboardService', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.reply_quality_trends import ReplyQualityTrendsService', 'from app.domains.customer_service.schemas.audit_logs import AuditLogRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.audit_logs import AuditLogService']

### automation_activity.py
- **domains**: `app/domains/customer_service/schemas/automation_activity.py` (42 lines)
  - classes: ['AutomationActivityEventRead', 'AutomationActivityRead']
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/automation_activity.py` (188 lines)
  - classes: ['CustomerServiceAutomationActivityService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.services.timeline import ConversationTimelineService']
- **api**: `app/api/products/customer_service/automation_activity.py` (39 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.schemas.automation_activity import AutomationActivityCategory, AutomationActivityRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal', 'from app.domains.customer_service.services.automation_activity import CustomerServiceAutomationActivityService']

### autopilot.py
- **domains**: `app/domains/customer_service/schemas/autopilot.py` (101 lines)
  - classes: ['AutopilotPolicyWrite', 'AutopilotPolicyRead', 'AutopilotEvaluationRequest', 'AutopilotDecisionRead', 'ConversationAutopilotDecisionRequest']
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/autopilot.py` (265 lines)
  - classes: ['CustomerServiceAutopilotService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import Conversation, CustomerServiceAutopilotPolicy', 'from app.domains.customer_service.repositories.audit_logs import AuditLogRepository', 'from app.domains.customer_service.schemas.autopilot import AutopilotDecisionRead, AutopilotEvaluationRequest, AutopilotPolicyWrite, ConversationAutopilotDecisionRequest', 'from app.domains.customer_service.services.conversation_intelligence import ConversationIntelligenceService']
- **api**: `app/api/products/customer_service/autopilot.py` (116 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.schemas.autopilot import AutopilotDecisionRead, AutopilotEvaluationRequest, AutopilotPolicyRead, AutopilotPolicyWrite, ConversationAutopilotDecisionRequest', 'from app.domains.customer_service.security.rbac import get_customer_service_principal, require_customer_service_permission', 'from app.domains.customer_service.services.autopilot import CustomerServiceAutopilotService']

### business_value.py
- **domains**: `app/domains/customer_service/schemas/business_value.py` (28 lines)
  - classes: ['RateMetric', 'BusinessValueAnalyticsRead']
  - top-level functions: []
- **api**: `app/api/products/customer_service/business_value.py` (32 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.schemas.business_value import BusinessValueAnalyticsRead', 'from app.domains.customer_service.security.rbac import require_customer_service_permission', 'from app.domains.customer_service.services.business_value_analytics import CustomerServiceBusinessValueAnalyticsService']

### commercial.py
- **domains**: `app/domains/customer_service/models/commercial.py` (478 lines)
  - classes: ['EmailWebhookReceipt', 'CustomerServiceSavedView', 'CustomerServiceAttachment', 'ConversationFollower', 'ConversationEditLease', 'CustomerServiceNotification', 'CustomerServiceSLACalendar', 'CustomerServiceMergeEvent', 'CustomerServiceCSATSurvey', 'CustomerServiceOnboardingState', 'WorkspaceSubscription', 'CustomerServicePrivacyRequest', 'CustomerServiceReplyDraft', 'CustomerServiceReplySignature']
  - top-level functions: []
- **domains**: `app/domains/customer_service/schemas/commercial.py` (94 lines)
  - classes: ['ReplySendRequest', 'SavedViewCreate', 'LeaseRequest', 'SLACalendarCreate', 'MergeRequest', 'ConversationSplitRequest', 'ResolutionRequest', 'CSATResponse', 'OnboardingUpdate', 'CustomerConsentUpdate', 'SubscriptionUpdate', 'PrivacyRequestCreate', 'NotificationCreate', 'ConversationFollowerRead']
  - top-level functions: []
- **api**: `app/api/products/customer_service/commercial.py` (490 lines)
  - classes: []
  - top-level functions: ['_service']
  - cross-tree imports: ['from app.domains.customer_service.schemas.commercial import ConversationSplitRequest, ConversationFollowerRead, CSATResponse, CustomerConsentUpdate, LeaseRequest, MergeRequest, NotificationCreate, OnboardingUpdate, PrivacyRequestCreate, ResolutionRequest, SavedViewCreate, SLACalendarCreate', 'from app.domains.customer_service.schemas.billing import ShopifyBillingCheckoutRead, ShopifyBillingCheckoutRequest, ShopifyBillingPortalRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user, require_customer_service_permission', 'from app.domains.customer_service.services.billing import BillingWebhookService', 'from app.domains.customer_service.services.shopify_billing import ShopifyBillingService', 'from app.domains.customer_service.services.commercial_operations import CommercialOperationsService']

### conversations.py
- **domains**: `app/domains/customer_service/repositories/conversations.py` (474 lines)
  - classes: ['ConversationMessageWriteResult', 'ConversationRepository']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import Conversation, ConversationMessage', 'from app.domains.customer_service.schemas.conversations import ConversationCreate, ConversationMessageCreate', 'from app.domains.customer_service.models.tickets import ConversationTag, Ticket, TicketAssignment', 'from app.domains.customer_service.models.quality import AgentAssistSuggestion, AgentAssistSuggestionRevision, CustomerServiceConversationInsight, CustomerServiceQualityReview, CustomerServiceSuggestedAction', 'from app.domains.customer_service.models.omnichannel import CustomerServiceExternalConversationLink, CustomerServiceExternalMessageLink', 'from app.domains.customer_service.models.chat import CustomerChatInboxLink', 'from app.domains.customer_service.models.sla import SLAViolation']
- **domains**: `app/domains/customer_service/schemas/conversations.py` (71 lines)
  - classes: ['ConversationCreate', 'ConversationRead', 'SenderType', 'ConversationMessageCreate', 'InternalNoteCreate', 'ConversationMessageRead']
  - top-level functions: []
- **api**: `app/api/products/customer_service/conversations.py` (505 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.schemas.agent_assist import AgentAssistSuggestionRead, AgentAssistSuggestionRevisionRead, AgentAssistSuggestionUpdate, ReplySuggestionResponse', 'from app.domains.customer_service.schemas.conversation_detail import ConversationDetail', 'from app.domains.customer_service.schemas.conversations import ConversationCreate, ConversationMessageCreate, ConversationMessageRead, InternalNoteCreate', 'from app.domains.customer_service.schemas.triage import TriageRequest, TriageResult', 'from app.domains.customer_service.schemas.commercial import ReplySendRequest', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.agent_assist import CustomerServiceAgentAssistService', 'from app.domains.customer_service.services.inbox import InboxService', 'from app.domains.customer_service.services.messaging import CustomerServiceMessagingService', 'from app.domains.customer_service.services.internal_notes import InternalNoteService', 'from app.domains.customer_service.services.triage import AutoTriageService', 'from app.domains.customer_service.schemas.tags import ConversationTagCreate, ConversationTagRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.tags import ConversationTagService', 'from app.domains.customer_service.schemas.timeline import ConversationTimelineEventRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.timeline import ConversationTimelineService', 'from app.domains.customer_service.schemas.conversation_context import ConversationContextRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.conversation_context import ConversationContextService', 'from app.domains.customer_service.schemas.workspace_recommendations import WorkspaceRecommendationsRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.workspace_recommendations import WorkspaceRecommendationsService']

### customers.py
- **domains**: `app/domains/customer_service/repositories/customers.py` (126 lines)
  - classes: ['CustomerRepository']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import Customer, Conversation, Ticket']
- **domains**: `app/domains/customer_service/schemas/customers.py` (65 lines)
  - classes: ['CustomerCreate', 'CustomerUpdate', 'CustomerRead']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import CustomerStatus']
- **domains**: `app/domains/customer_service/services/customers.py` (39 lines)
  - classes: ['CustomerService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import Customer', 'from app.domains.customer_service.repositories.customers import CustomerRepository']
- **api**: `app/api/products/customer_service/customers.py` (164 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.schemas.customer_360 import Customer360Read', 'from app.domains.customer_service.schemas.customer_activity import CustomerActivityEventRead', 'from app.domains.customer_service.schemas.customer_risk import CustomerRiskLeaderboardItem, CustomerRiskRead', 'from app.domains.customer_service.schemas.customer_summary import CustomerSummaryRead', 'from app.domains.customer_service.schemas.customers import CustomerCreate, CustomerRead', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.customer_360 import Customer360Service', 'from app.domains.customer_service.services.customer_activity import CustomerActivityService', 'from app.domains.customer_service.services.customer_risk import CustomerRiskService', 'from app.domains.customer_service.services.customers import CustomerService']

### email_identity.py
- **domains**: `app/domains/customer_service/schemas/email_identity.py` (32 lines)
  - classes: ['EmailIdentityUpdate', 'EmailIdentityRead']
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/email_identity.py` (87 lines)
  - classes: ['CustomerServiceEmailIdentityService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import CustomerServiceEmailIdentity']
- **api**: `app/api/products/customer_service/email_identity.py` (54 lines)
  - classes: []
  - top-level functions: ['_require_admin']
  - cross-tree imports: ['from app.domains.customer_service.schemas.email_identity import EmailIdentityRead, EmailIdentityUpdate', 'from app.domains.customer_service.services.email_identity import CustomerServiceEmailIdentityService']

### helpdesk.py
- **domains**: `app/domains/customer_service/schemas/helpdesk.py` (87 lines)
  - classes: ['ConversationSnoozeRequest', 'ConversationModerationRequest', 'BulkConversationActionRequest', 'ReplyDraftWrite', 'ReplyDraftScheduleRequest', 'ReplyDraftRead', 'ReplySignatureWrite', 'ReplySignatureRead', 'CustomerCustomFieldsUpdate']
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/helpdesk.py` (805 lines)
  - classes: ['CustomerServiceModerationService', 'CustomerServiceHelpdeskService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import Conversation, ConversationTag, Customer, CustomerServiceAuditLog, CustomerServiceReplyDraft, CustomerServiceReplySignature, Ticket, TicketAssignment', 'from app.domains.customer_service.schemas.commercial import ReplySendRequest', 'from app.domains.customer_service.schemas.helpdesk import BulkConversationActionRequest, ConversationModerationRequest, ConversationSnoozeRequest, ReplyDraftWrite, ReplySignatureWrite', 'from app.domains.customer_service.services.messaging import CustomerServiceMessagingService', 'from app.domains.customer_service.jobs.handlers import CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB']
- **api**: `app/api/products/customer_service/helpdesk.py` (219 lines)
  - classes: []
  - top-level functions: ['_service']
  - cross-tree imports: ['from app.domains.customer_service.schemas.helpdesk import BulkConversationActionRequest, ConversationModerationRequest, ConversationSnoozeRequest, CustomerCustomFieldsUpdate, ReplyDraftRead, ReplyDraftScheduleRequest, ReplyDraftWrite, ReplySignatureRead, ReplySignatureWrite', 'from app.domains.customer_service.security.rbac import get_customer_service_principal, require_customer_service_permission', 'from app.domains.customer_service.services.helpdesk import CustomerServiceHelpdeskService']

### inbox.py
- **domains**: `app/domains/customer_service/repositories/inbox.py` (145 lines)
  - classes: ['InboxRepository']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import Conversation, ConversationMessage, Ticket']
- **domains**: `app/domains/customer_service/schemas/inbox.py` (29 lines)
  - classes: ['InboxTicketSummary', 'InboxItem']
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/inbox.py` (275 lines)
  - classes: ['InboxService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.repositories.conversations import ConversationRepository', 'from app.domains.customer_service.repositories.customers import CustomerRepository', 'from app.domains.customer_service.repositories.inbox import InboxRepository', 'from app.domains.customer_service.repositories.tickets import TicketRepository', 'from app.domains.customer_service.schemas.conversations import ConversationCreate', 'from app.domains.customer_service.schemas.tickets import TicketCreate', 'from app.domains.customer_service.services.sla import SLAService', 'from app.domains.customer_service.repositories.chat_repository import ChatRepository', 'from app.domains.customer_service.services.chat_service import CustomerChatService', 'from app.domains.customer_service.realtime.publisher import CustomerServiceRealtimePublisher']
- **api**: `app/api/products/customer_service/inbox.py` (246 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.inbox.schemas import InboundEmailIngestResult, NormalizedInboundEmail', 'from app.domains.customer_service.inbox.service import InboundEmailIngestService', 'from app.domains.customer_service.schemas.inbox import InboxItem', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.inbox import InboxService', 'from app.domains.customer_service.services.messaging import CustomerServiceMessagingService', 'from app.domains.customer_service.repositories.tickets import TicketRepository', 'from app.domains.customer_service.schemas.routing import AutoAssignRequest, AutoAssignResult', 'from app.domains.customer_service.schemas.tickets import TicketRead, TicketUpdate', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.assignment import AssignmentService', 'from app.domains.customer_service.services.routing import CustomerServiceRoutingService', 'from app.domains.customer_service.schemas.shipping import ShippingTrackingRead, ShippingTrackRequest', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.shipping import ShippingService']

### knowledge.py
- **domains**: `app/domains/customer_service/schemas/knowledge.py` (89 lines)
  - classes: ['CustomerServiceKnowledgeSearchRequest', 'CustomerServiceKnowledgeHit', 'CustomerServiceKnowledgeContext', 'KnowledgeURLIngestRequest', 'KnowledgeInlineIngestRequest', 'KnowledgeSourceRead', 'KnowledgeSettingsUpdate', 'KnowledgeSettingsRead', 'KnowledgeEvaluationQuestionCreate', 'KnowledgeEvaluationQuestionRead']
  - top-level functions: []
- **domains**: `app/domains/customer_service/services/knowledge.py` (548 lines)
  - classes: ['_HTMLTextExtractor', 'CustomerServiceKnowledgeService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.integrations.shopify.provider_factory import ShopifyProviderFactory', 'from app.domains.customer_service.models import CustomerServiceKnowledgeEvaluationQuestion, CustomerServiceKnowledgeSettings, CustomerServiceKnowledgeSource', 'from app.domains.customer_service.repositories.shopify import ShopifyRepository']
- **api**: `app/api/products/customer_service/knowledge.py` (214 lines)
  - classes: []
  - top-level functions: ['_require_admin']
  - cross-tree imports: ['from app.domains.customer_service.schemas.knowledge import CustomerServiceKnowledgeContext, CustomerServiceKnowledgeSearchRequest, KnowledgeEvaluationQuestionCreate, KnowledgeEvaluationQuestionRead, KnowledgeInlineIngestRequest, KnowledgeSettingsRead, KnowledgeSettingsUpdate, KnowledgeSourceRead, KnowledgeURLIngestRequest', 'from app.domains.customer_service.services.knowledge import CustomerServiceKnowledgeService', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user']

### proactive.py
- **domains**: `app/domains/customer_service/schemas/proactive.py` (62 lines)
  - classes: ['ProactiveAction', 'ProactivePolicyWrite', 'ProactivePolicyRead', 'ProactiveIncidentRead']
  - top-level functions: []
- **api**: `app/api/products/customer_service/proactive.py` (100 lines)
  - classes: []
  - top-level functions: ['_service']
  - cross-tree imports: ['from app.domains.customer_service.schemas.proactive import ProactiveIncidentRead, ProactivePolicyRead, ProactivePolicyWrite', 'from app.domains.customer_service.security.rbac import require_customer_service_permission', 'from app.domains.customer_service.services.proactive_playbooks import CustomerServiceProactivePlaybookService']

### product.py
- **domains**: `app/domains/customer_service/product.py` (54 lines)
  - classes: []
  - top-level functions: ['customer_service_product_contract']
- **api**: `app/api/products/customer_service/product.py` (16 lines)
  - classes: []
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.product import customer_service_product_contract', 'from app.domains.customer_service.security.rbac import get_customer_service_principal']

### shopify.py
- **domains**: `app/domains/customer_service/models/shopify.py` (237 lines)
  - classes: ['CustomerServiceShopifyConnection', 'ShopifyOAuthInstallSession', 'ShopifyWebhookReceipt', 'CustomerServiceShopifyOrderCache', 'CustomerServiceShippingTrackingCache']
  - top-level functions: []
- **domains**: `app/domains/customer_service/providers/shopify.py` (266 lines)
  - classes: ['ShopifyProvider', 'FakeShopifyProvider']
  - top-level functions: []
- **domains**: `app/domains/customer_service/repositories/shopify.py` (192 lines)
  - classes: ['ShopifyRepository']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.models import CustomerServiceShopifyConnection, CustomerServiceShopifyOrderCache']
- **domains**: `app/domains/customer_service/schemas/shopify.py` (93 lines)
  - classes: ['ShopifyConnectionCreate', 'ShopifyConnectionRead', 'ShopifyOrderRead', 'ShopifyActionRequest', 'ShopifyActionRead', 'ShopifySupportWorkflowPrepareRequest', 'ShopifySupportWorkflowPrepareRead', 'ShopifyInstallRequest', 'ShopifyInstallRead', 'ShopifyOAuthCallbackRead', 'ShopifyConnectionTestRead']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.services.shopify_action_scope import ShopifyActionScope']
- **domains**: `app/domains/customer_service/services/shopify.py` (665 lines)
  - classes: ['ShopifyService']
  - top-level functions: []
  - cross-tree imports: ['from app.domains.customer_service.integrations.shopify.provider_factory import ShopifyProviderFactory', 'from app.domains.customer_service.models import CustomerServiceAuditLog', 'from app.domains.customer_service.providers.shopify import ShopifyProvider', 'from app.domains.customer_service.repositories.chat_repository import ChatRepository', 'from app.domains.customer_service.repositories.shopify import ShopifyRepository', 'from app.domains.customer_service.services.chat_service import CustomerChatService', 'from app.domains.customer_service.services.shopify_order_context import ShopifyOrderContextBuilder', 'from app.domains.customer_service.services.shopify_provider_installation import ShopifyProviderInstallationProjector', 'from app.domains.customer_service.services.shopify_provider_lifecycle import ShopifyProviderLifecycleEvents', 'from app.domains.customer_service.services.shopify_support_orchestrator import ShopifySupportWorkflowOrchestrator']
- **api**: `app/api/products/customer_service/providers/shopify.py` (433 lines)
  - classes: []
  - top-level functions: ['_shopify_oauth_service']
  - cross-tree imports: ['from app.domains.customer_service.integrations.shopify.lifecycle import InvalidShopifyStateError, consume_install_state, create_install_state, process_compliance_webhook, verify_webhook_hmac', 'from app.domains.customer_service.integrations.shopify.oauth import ShopifyOAuthService', 'from app.domains.customer_service.schemas.shopify import ShopifyActionRead, ShopifyActionRequest, ShopifyConnectionCreate, ShopifyConnectionRead, ShopifyConnectionTestRead, ShopifyInstallRead, ShopifyInstallRequest, ShopifyOAuthCallbackRead, ShopifyOrderRead, ShopifySupportWorkflowPrepareRead, ShopifySupportWorkflowPrepareRequest', 'from app.domains.customer_service.security.rbac import get_customer_service_principal as get_current_user', 'from app.domains.customer_service.services.shopify import ShopifyService', 'from app.domains.customer_service.services.shopify_billing import ShopifyBillingService', 'from app.domains.customer_service.repositories.shopify import ShopifyRepository']

## Filenames only in domains/customer_service: 159
action_observability.py, agent_assist.py, agent_capacity.py, agents.py, ai_context_policy.py, ai_replies.py, ai_reply_composer.py, ai_reply_regenerate.py, ai_reply_regeneration.py, assignment.py, attachment_storage.py, audit_logs.py, base.py, best_agent_selector.py, billing.py, billing_plans.py, business_value_analytics.py, chat.py, chat_repository.py, chat_service.py, chatbot_workflow_catalog.py, client.py, commerce.py, commerce_defaults.py, commerce_order.py, commercial_operations.py, conversation_context.py, conversation_detail.py, conversation_intelligence.py, conversation_intelligence_snapshot.py, conversation_summary.py, core.py, customer_360.py, customer_activity.py, customer_chat.py, customer_identities.py, customer_identity.py, customer_risk.py, customer_summary.py, customer_support_business_learning.py, customer_support_business_learning_projection.py, customer_support_clarification.py, customer_support_commerce_context.py, customer_support_intake.py, customer_support_objective.py, customer_support_objective_learning_candidate_generation.py, customer_support_objective_learning_durable_policy_generation.py, customer_support_objective_learning_policy_bootstrap.py, customer_support_objective_learning_recording.py, customer_support_objective_learning_source_loader.py, customer_support_operation_graph.py, customer_support_orchestration.py, customer_support_outcome.py, customer_support_outcome_evaluation.py, customer_support_outcome_evaluation_service.py, customer_support_outcome_evaluations.py, customer_support_outcome_recording.py, customer_support_outcomes.py, customer_support_product_planner.py, customer_support_product_planner_registry.py, customer_support_resolution.py, customer_support_resolution_assessment.py, customer_support_resolution_projection.py, customer_support_review_plan.py, customer_support_review_plan_loader.py, customer_support_review_workflow.py, dashboard.py, engine.py, enums.py, errors.py, event_subscriptions.py, events.py, generic.py, handlers.py, instagram.py, internal_notes.py, knowledge_agent_mcp.py, launch.py, lifecycle.py, lifecycle_projection.py, macros.py, management.py, matcher.py, message_classifier.py, messaging.py, models.py, notifications.py, oauth.py, objective_learning.py, objective_learning_extraction.py, objective_learning_profiles.py, omnichannel.py, omnichannel_job_types.py, omnichannel_jobs.py, order_ref.py, outcomes.py, planner.py, planning.py, proactive_playbooks.py, product_control.py, protocol.py, provider_factory.py, providers.py, publisher.py, quality.py, quality_reviews.py, queues.py, rbac.py, real_provider.py, registration.py, registry.py, reply_quality.py, reply_quality_dashboard.py, reply_quality_insights.py, reply_quality_trends.py, reply_suggestion_workflow.py, retry.py, retry_policy.py, review_plan.py, routing.py, routing_policies.py, runtime_bridge.py, schemas.py, selector.py, service.py, shipping.py, shopify_action_scope.py, shopify_action_workflows.py, shopify_billing.py, shopify_commerce.py, shopify_context.py, shopify_order_context.py, shopify_provider_installation.py, shopify_provider_lifecycle.py, shopify_provider_verification.py, shopify_support_orchestrator.py, shopify_workflow_catalog.py, shopify_workflow_decisions.py, signatures.py, sla.py, structured_intelligence.py, suggested_actions.py, tags.py, teams.py, threading.py, ticket_assignment.py, tickets.py, timeline.py, triage.py, trigger_handlers.py, webhooks.py, whatsapp.py, workflow.py, workflow_executions.py, workflow_mapper.py, workflow_templates.py, workflows.py, workload.py, workspace_recommendations.py

## Filenames only in api/products/customer_service: 6
automation.py, channels.py, intelligence.py, learning.py, router.py, workforce.py
