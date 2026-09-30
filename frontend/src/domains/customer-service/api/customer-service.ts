import { ApiError, apiJson, jsonBody } from "@/platform/api/client";


import type {
  UUID,
  InboxTicketSummary,
  InboxItem,
  ConversationDetailCustomer,
  ConversationDetailMessage,
  ConversationDetailTicket,
  ConversationDetail,
  ConversationTag,
  AIReplyComposeResponse,
  AIReplyRegenerateResponse,
  ShopifyOrderRead,
  ConversationSummary,
  ConversationInsight,
  SuggestedAction,
  WorkflowWait,
  WorkflowExecution,
  SLAViolation,
  ChannelConnection,
  ProviderCapability,
  WorkflowTemplate,
  SeedWorkflowTemplatesResponse,
  Agent,
  Team,
  Queue,
  RoutingPolicy,
  ShopifyOrder,
  ShopifyActionResponse,
  OmnichannelInboundResult,
  ConversationMessageCreate,
  UploadedConversationAttachment,
  ConversationContext,
  AutomationActivity,
  CustomerSummary,
  ApprovalDecisionResult,
  InboxFolder,
} from "@/domains/customer-service/model";

export type {
  UUID,
  InboxTicketSummary,
  InboxItem,
  ConversationDetailCustomer,
  ConversationDetailMessage,
  ConversationDetailTicket,
  ConversationDetail,
  ConversationTag,
  AIReplyComposeResponse,
  AIReplyRegenerateResponse,
  ShopifyOrderRead,
  ConversationSummary,
  ConversationInsight,
  SuggestedAction,
  WorkflowWait,
  WorkflowExecution,
  SLAViolation,
  ChannelConnection,
  ProviderCapability,
  WorkflowTemplate,
  SeedWorkflowTemplatesResponse,
  Agent,
  Team,
  Queue,
  RoutingPolicy,
  ShopifyOrder,
  ShopifyActionResponse,
  OmnichannelInboundResult,
  ConversationMessageCreate,
  ConversationContext,
  AutomationActivity,
  CustomerSummary,
  ApprovalDecisionResult,
  InboxFolder,
};

const base = "/api/customer-service";

export const customerServiceApi = {


  createAgent(payload: Record<string, unknown>) {
    return apiJson<Agent>(`${base}/agents`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },

  createTeam(payload: Record<string, unknown>) {
    return apiJson<Team>(`${base}/teams`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },

  createQueue(payload: Record<string, unknown>) {
    return apiJson<Queue>(`${base}/queues`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },

  createRoutingPolicy(payload: Record<string, unknown>) {
    return apiJson<RoutingPolicy>(`${base}/routing-policies`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },



  channels() {
    return apiJson<{ channels: string[] }>(`${base}/channels/`);
  },

  channelConnections() {
    return apiJson<ChannelConnection[]>(`${base}/omnichannel/connections`);
  },

  createChannelConnection(payload: Record<string, unknown>) {
    return apiJson<ChannelConnection>(`${base}/omnichannel/connections`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },

  providerCapabilities() {
    return apiJson<ProviderCapability[]>(`${base}/omnichannel/providers/capabilities`);
  },

  emailIdentity() {
    return apiJson<any>(`${base}/email/identity`);
  },

  configureEmailIdentity(payload: Record<string, unknown>) {
    return apiJson<any>(`${base}/email/identity`, {
      method: "PUT",
      body: jsonBody(payload),
    });
  },

  verifyEmailIdentity() {
    return apiJson<any>(`${base}/email/identity/verify`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  workflowTemplates() {
    return apiJson<WorkflowTemplate[]>(`${base}/workflow-templates`);
  },

  seedShopifyTemplates() {
    return apiJson<SeedWorkflowTemplatesResponse>(
      `${base}/workflow-templates/seed-shopify`,
      {
        method: "POST",
      },
    );
  },

  seedShopifyWorkflowTemplates() {
    return apiJson<SeedWorkflowTemplatesResponse>(`${base}/workflow-templates/seed-shopify`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  seedWebsiteChatWorkflowTemplates() {
    return apiJson<SeedWorkflowTemplatesResponse>(`${base}/workflow-templates/seed-website-chat`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  cloneWorkflowTemplate(templateId: UUID, payload: Record<string, unknown> = {}) {
    return apiJson<WorkflowTemplate>(`${base}/workflow-templates/${templateId}/clone`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },

  updateWorkflowTemplate(templateId: UUID, payload: Partial<WorkflowTemplate>) {
    return apiJson<WorkflowTemplate>(`${base}/workflow-templates/${templateId}`, {
      method: "PATCH",
      body: jsonBody(payload),
    });
  },

  publishWorkflowTemplate(templateId: UUID) {
    return apiJson<WorkflowTemplate>(`${base}/workflow-templates/${templateId}/publish`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  unpublishWorkflowTemplate(templateId: UUID) {
    return apiJson<WorkflowTemplate>(`${base}/workflow-templates/${templateId}/unpublish`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  agents() {
    return apiJson<Agent[]>(`${base}/agents`);
  },

  teams() {
    return apiJson<Team[]>(`${base}/teams`);
  },

  queues() {
    return apiJson<Queue[]>(`${base}/queues`);
  },

  routingPolicies() {
    return apiJson<RoutingPolicy[]>(`${base}/routing-policies`);
  },

  inbox(folder: InboxFolder = "inbox") {
    return apiJson<InboxItem[]>(`${base}/inbox/?folder=${folder}`);
  },

  conversation(conversationId: UUID) {
    return apiJson<ConversationDetail>(`${base}/conversations/${conversationId}`);
  },

  conversationContext(conversationId: UUID) {
    return apiJson<ConversationContext>(`${base}/conversations/${conversationId}/context`);
  },

  automationActivity(conversationId: UUID, limit = 200) {
    return apiJson<AutomationActivity>(
      `${base}/conversations/${conversationId}/automation-activity?limit=${limit}`,
    );
  },

  customerSummary(customerId: UUID) {
    return apiJson<CustomerSummary>(`${base}/customers/${customerId}/summary`);
  },

  deleteConversation(conversationId: UUID) {
    return apiJson(`${base}/conversations/${conversationId}`, {
      method: "DELETE",
    });
  },

  tags(conversationId: UUID) {
    return apiJson<ConversationTag[]>(`${base}/conversations/${conversationId}/tags/`);
  },


  insights(conversationId: UUID) {
    return apiJson<ConversationInsight[]>(
      `${base}/conversations/${conversationId}/intelligence`,
    );
  },

  analyzeConversation(conversationId: UUID) {
    return apiJson<ConversationInsight>(
      `${base}/conversations/${conversationId}/intelligence/analyze`,
      { method: "POST", body: jsonBody({}) },
    );
  },

  suggestedActions(conversationId: UUID) {
    return apiJson<SuggestedAction[]>(
      `${base}/conversations/${conversationId}/suggested-actions`,
    );
  },

  generateSuggestedActions(conversationId: UUID) {
    return apiJson<SuggestedAction[]>(
      `${base}/conversations/${conversationId}/suggested-actions/generate`,
      { method: "POST", body: jsonBody({}) },
    );
  },


  acceptSuggestedAction(actionId: UUID) {
    return apiJson<SuggestedAction>(
      `${base}/suggested-actions/${actionId}/accept`,
      { method: "POST", body: jsonBody({}) },
    );
  },

  rejectSuggestedAction(actionId: UUID) {
    return apiJson<SuggestedAction>(
      `${base}/suggested-actions/${actionId}/reject`,
      { method: "POST", body: jsonBody({}) },
    );
  },

  executeSuggestedAction(actionId: UUID, payload: Record<string, unknown> = {}) {
    return apiJson<SuggestedAction>(
      `${base}/suggested-actions/${actionId}/execute`,
      { method: "POST", body: jsonBody({ payload }) },
    );
  },

  workflowExecutions(conversationId: UUID) {
    return apiJson<WorkflowExecution[]>(
      `${base}/conversations/${conversationId}/workflow-executions`,
    );
  },

  runWorkflowTemplateForConversation(
    conversationId: UUID,
    payload: {
      template_id: UUID;
      message?: string | null;
    },
  ) {
    return apiJson<WorkflowExecution>(
      `${base}/conversations/${conversationId}/workflow-executions/run-template`,
      {
        method: "POST",
        body: jsonBody(payload),
      },
    );
  },

  workflowApprovals(status = "waiting") {
    return apiJson<WorkflowWait[]>(
      `${base}/workflow-approvals?status=${encodeURIComponent(status)}`,
    );
  },

  approveWorkflowApproval(waitId: string) {
    return apiJson<ApprovalDecisionResult>(
      `${base}/workflow-approvals/${waitId}/approve`,
      { method: "POST" },
    );
  },

  rejectWorkflowApproval(waitId: string) {
    return apiJson<ApprovalDecisionResult>(
      `${base}/workflow-approvals/${waitId}/reject`,
      { method: "POST" },
    );
  },


  slaViolations(status?: string) {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return apiJson<SLAViolation[]>(`${base}/sla/violations${query}`);
  },

  reopenTicket(ticketId: UUID) {
    return apiJson(`${base}/tickets/${ticketId}/reopen`, {
      method: "POST",
      body: jsonBody({}),
    });
  },


  closeTicket(ticketId: UUID) {
    return apiJson(`${base}/tickets/${ticketId}/close`, {
      method: "POST",
      body: jsonBody({}),
    });
  },


  assignTicket(ticketId: UUID, assignedTo: UUID) {
    return apiJson(`${base}/tickets/${ticketId}/assign?assigned_to=${encodeURIComponent(assignedTo)}`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  autoAssignTicket(ticketId: UUID) {
    return apiJson(`${base}/tickets/${ticketId}/auto-assign`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  updateTicket(ticketId: UUID, payload: { status?: string; priority?: string; assigned_to?: string | null }) {
    return apiJson(`${base}/tickets/${ticketId}`, {
      method: "PATCH",
      body: jsonBody(payload),
    });
  },


  checkSLA() {
    return apiJson<SLAViolation[]>(`${base}/sla/check`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  analytics() {
    return apiJson<any>(`${base}/analytics/`);
  },

  workloadReport() {
    return apiJson<any[]>(`${base}/analytics/workload`);
  },

  auditLogs(limit = 100) {
    return apiJson<any[]>(`${base}/audit-logs/?limit=${limit}`);
  },

  notifications(unreadOnly = false) {
    const query = unreadOnly ? "?unread_only=true" : "";
    return apiJson<any[]>(`${base}/notifications${query}`);
  },

  markNotificationRead(notificationId: UUID) {
    return apiJson(`${base}/notifications/${notificationId}/read`, {
      method: "POST",
      body: jsonBody({}),
    });
  },

  subscription() {
    return apiJson<any>(`${base}/subscription`);
  },

  billingCheckout(plan: "starter" | "growth" | "pro") {
    return apiJson<{ confirmation_url: string }>(`${base}/billing/shopify/checkout`, {
      method: "POST",
      body: jsonBody({ plan }),
    });
  },

  billingPortal() {
    return apiJson<{ manage_url: string }>(`${base}/billing/shopify/portal`);
  },




  startShopifyInstall(shopDomain: string) {
    return apiJson<{ shop_domain: string; install_url: string; state: string }>(
      `${base}/shopify/install`,
      {
        method: "POST",
        body: jsonBody({ shop_domain: shopDomain }),
      },
    );
  },

  shopifyOrder(orderRef: string) {
    return apiJson<ShopifyOrder>(
      `${base}/shopify/orders/${encodeURIComponent(encodeURIComponent(orderRef))}`,
    );
  },

  // Mutating Shopify actions need an idempotency key and a resolved approval, so the
  // inbox only calls the read-only shipping status action directly.
  shopifyShippingStatus(orderRef: string) {
    return apiJson<ShopifyActionResponse>(
      `${base}/shopify/orders/${encodeURIComponent(encodeURIComponent(orderRef))}/actions/shipping_status`,
      {
        method: "POST",
        body: jsonBody({ order_ref: orderRef }),
      },
    );
  },

  composeAIReply(
    conversationId: UUID,
    customerMessage?: string | null,
    shopifyContext?: Record<string, unknown> | null,
  ) {
    return apiJson<AIReplyComposeResponse>(
      `${base}/conversations/${conversationId}/ai-replies/compose`,
      {
        method: "POST",
        body: jsonBody({
          customer_message: customerMessage ?? null,
          shopify_context: shopifyContext ?? null,
          force_refresh_intelligence: false,
        }),
      },
    );
  },

  regenerateAIReply(conversationId: UUID) {
    return apiJson<AIReplyRegenerateResponse>(
      `${base}/conversations/${conversationId}/ai-replies/regenerate`,
      { method: "POST", body: jsonBody({}) },
    );
  },




  ingestInboundMessage(payload: Record<string, unknown>) {
    return apiJson<OmnichannelInboundResult>(`${base}/omnichannel/inbound`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },

  sendMessage(conversationId: UUID, payload: ConversationMessageCreate) {
    return apiJson(`${base}/conversations/${conversationId}/messages`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },

  async uploadConversationAttachment(conversationId: UUID, file: File) {
    const form = new FormData();
    form.append("upload", file);
    const response = await fetch(`${base}/conversations/${conversationId}/attachments`, {
      method: "POST",
      credentials: "include",
      body: form,
    });
    const text = await response.text();
    if (!response.ok) {
      throw new ApiError(response.status, text);
    }
    return JSON.parse(text) as UploadedConversationAttachment;
  },

  enqueueOutboundMessage(payload: {
    conversation_id: UUID;
    body: string;
    sender_type?: "agent" | "ai" | "system";
    idempotency_key: string;
    attachments: { attachment_id: UUID }[];
    meta?: Record<string, unknown> | null;
  }) {
    return apiJson(`${base}/omnichannel/outbound/enqueue`, {
      method: "POST",
      body: jsonBody(payload),
    });
  },


  addInternalNote(conversationId: UUID, body: string, meta: Record<string, unknown> | null = null) {
    return apiJson(`${base}/conversations/${conversationId}/internal-notes`, {
      method: "POST",
      body: jsonBody({ body, meta }),
    });
  },

  addTag(conversationId: UUID, name: string) {
    return apiJson<ConversationTag>(`${base}/conversations/${conversationId}/tags/`, {
      method: "POST",
      body: jsonBody({ name }),
    });
  },

  removeTag(conversationId: UUID, name: string) {
    return apiJson(`${base}/conversations/${conversationId}/tags/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
  },

  snoozeConversation(conversationId: UUID, until: string, reason?: string) {
    return apiJson(`${base}/conversations/${conversationId}/snooze`, {
      method: "POST",
      body: jsonBody({ until, reason }),
    });
  },

  wakeConversation(conversationId: UUID) {
    return apiJson(`${base}/conversations/${conversationId}/snooze`, {
      method: "DELETE",
    });
  },
};

export type {
  ChatWidgetSettings,
  ChatWidgetSettingsUpdate,
} from "@/platform/api/customer-service-chat-widget";

export {
  getChatWidgetSettings,
  updateChatWidgetSettings,
  listWorkflowTemplates,
  seedShopifyWorkflowTemplates,
} from "@/platform/api/customer-service-chat-widget";
