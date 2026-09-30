export type UUID = string;

export type InboxTicketSummary = {
  id: UUID;
  status: string;
  priority: string;
  assigned_to: string | null;
};

export type InboxItem = {
  conversation_id: UUID;
  customer_id: UUID;
  customer_name: string | null;
  customer_email: string | null;
  channel: string;
  subject: string | null;
  status: string;
  latest_message: string | null;
  created_at: string;
  updated_at: string;
  snoozed_until: string | null;
  moderation_status: string;
  moderation_reason: string | null;
  tags: string[];
  topic: string | null;
  ticket: InboxTicketSummary | null;
};

export type InboxFolder = "inbox" | "snoozed" | "spam" | "all";

export type ConversationDetailCustomer = {
  id: UUID;
  name: string | null;
  email: string | null;
  phone: string | null;
};

export type ConversationDetailMessage = {
  id: UUID;
  sender_type: string;
  body: string;
  meta: Record<string, unknown> | null;
  created_at: string;
};

export type ConversationDetailTicket = {
  id: UUID;
  title: string;
  status: string;
  priority: string;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationDetail = {
  id: UUID;
  customer_id: UUID;
  channel: string;
  subject: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  customer: ConversationDetailCustomer | null;
  messages: ConversationDetailMessage[];
  ticket: ConversationDetailTicket | null;
};

export type ConversationTag = {
  id: UUID;
  user_id: UUID;
  conversation_id: UUID;
  name: string;
  created_at: string;
};

export type AIReplyComposeResponse = {
  body: string;
  confidence: number;
  reply_type: string;
  requires_review: boolean;
  source_summary: Record<string, unknown>;
  sources: Record<string, unknown>;
};


export type AIReplyRegenerateResponse = {
  body: string;
  confidence: number;
  generation: number;
  regenerated: boolean;
  sources: Record<string, unknown>;
};

export type ShopifyTrackingInfo = {
  tracking_number: string | null;
  tracking_url: string | null;
  carrier: string | null;
  status: string | null;
};

export type ShopifyOrderContext = {
  order_id: string;
  order_name: string | null;
  customer_email: string | null;
  financial_status: string | null;
  fulfillment_status: string | null;
  total_price: string | null;
  currency: string | null;
  shipping_address: Record<string, unknown> | null;
  tracking: ShopifyTrackingInfo;
  is_paid: boolean;
  is_fulfilled: boolean;
  can_refund: boolean;
  can_cancel: boolean;
  can_change_address: boolean;
  raw: Record<string, unknown>;
};

export type ShopifyOrderRead = {
  order_id: string;
  order_name: string | null;
  customer_email: string | null;
  payload: Record<string, unknown>;
  context: ShopifyOrderContext | null;
  connection_id?: UUID | null;
};


export type ConversationSummary = {
  summary: string;
  intent: string | null;
  sentiment: string | null;
  urgency: string | null;
  entities: Record<string, unknown>;
};

export type ConversationInsight = {
  id: UUID;
  conversation_id: UUID;
  intent: string | null;
  sentiment: string | null;
  urgency: string | null;
  summary: string | null;
  root_cause?: string | null;
  entities?: Record<string, unknown> | null;
  risks?: Record<string, unknown> | null;
  opportunities?: Record<string, unknown> | null;
  confidence: number | null;
  source?: string | null;
  language?: string | null;
  model_version?: string | null;
  fallback_reason?: string | null;
  created_at: string;
  updated_at?: string;
};

export type SuggestedActionAutopilot = {
  decision?: string | null;
  requires_approval?: boolean | null;
  may_execute?: boolean | null;
  may_send?: boolean | null;
  risk?: string | null;
  reason_codes?: string[] | null;
  matched_intent?: string | null;
  policy_id?: string | null;
  requested_mode?: string | null;
  action_kind?: string | null;
  confidence?: number | null;
};

export type SuggestedAction = {
  id: UUID;
  conversation_id: UUID;
  action_type: string;
  title: string;
  description: string | null;
  status: string;
  confidence: number | null;
  source?: string | null;
  payload: (Record<string, unknown> & {
    order_ref?: string | null;
    reason?: string | null;
    urgency?: string | null;
    autopilot?: SuggestedActionAutopilot | null;
  }) | null;
  created_at: string;
  updated_at?: string | null;
};

export type WorkflowWait = {
  id: UUID;
  user_id: UUID;
  workflow_run_id: string;
  node_id?: string | null;
  wait_type: string;
  status: string;
  payload: Record<string, unknown>;
  resolution?: Record<string, unknown> | null;
  expires_at?: string | null;
  resolved_at?: string | null;
  created_at: string;
};

export type WorkflowExecution = {
  id?: UUID;

  job_id?: UUID;
  workflow_run_id?: UUID | null;
  user_id?: UUID | null;

  conversation_id?: UUID | null;
  ticket_id?: UUID | null;
  customer_id?: UUID | null;

  workflow_template_id?: UUID;
  workflow_name?: string | null;
  template_name?: string | null;

  status: string;
  job_type?: string;

  event_type?: string | null;
  trigger_event_type?: string | null;
  subscription_name?: string | null;
  workflow_version?: number | null;
  handed_over?: boolean;
  waiting_approval?: boolean;
  channel?: string | null;

  message?: string | null;
  error_message?: string | null;

  attempts?: number;
  max_attempts?: number;

  payload?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  meta?: Record<string, unknown> | null;

  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string;
};


export type SLAViolation = {
  id: UUID;
  user_id: UUID;
  ticket_id: UUID;
  policy_id: UUID | null;
  target_type: string;
  due_at: string;
  breached_at: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};






export type ChannelConnection = {
  id: UUID;
  user_id: UUID;
  channel: string;
  external_account_id: string;
  display_name: string | null;
  status: string;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type ProviderCapability = {
  provider?: string;
  channel?: string;
  name?: string;
  supports_inbound?: boolean;
  supports_outbound?: boolean;
  supports_delivery_events?: boolean;
  [key: string]: unknown;
};

export type WorkflowTemplate = {
  id: UUID;
  category: string;
  name: string;
  description: string | null;
  workflow_json: Record<string, unknown>;
  tags: string[] | null;
  scope: string;
  version: string;
  status: string;
  created_at: string;
};

export type SeedWorkflowTemplatesResponse = {
  created: WorkflowTemplate[];
  existing: WorkflowTemplate[];
  created_count: number;
  existing_count: number;
};

export type Agent = {
  id: UUID;
  user_id: UUID;
  agent_user_id: UUID;
  display_name: string;
  email: string | null;
  status: string;
  availability: string;
  skills: string[];
  channels: string[];
  languages: string[];
  max_open_tickets: number;
  meta: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type Team = {
  id: UUID;
  user_id: UUID;
  name: string;
  description: string | null;
  is_active: boolean;
  meta: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type Queue = {
  id: UUID;
  user_id: UUID;
  name: string;
  description: string | null;
  team_id: UUID | null;
  channel: string | null;
  intent: string | null;
  priority: string | null;
  priority_rank: number;
  is_default: boolean;
  is_active: boolean;
  filters: Record<string, unknown> | null;
  meta: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type RoutingPolicy = {
  id: UUID;
  user_id: UUID;
  name: string;
  channel: string | null;
  intent: string | null;
  priority: string | null;
  strategy: string;
  candidate_assignee_ids: UUID[];
  candidate_team_ids: UUID[];
  candidate_queue_ids: UUID[];
  priority_rank: number;
  is_fallback: boolean;
  is_active: boolean;
  filters: Record<string, unknown> | null;
  meta: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type ShopifyOrder = ShopifyOrderRead;

export type ShopifyActionResponse = {
  action: string;
  order_id: string;
  order_name: string | null;
  status: string;
  message: string;
  payload: Record<string, unknown>;
};


export type OmnichannelInboundResult = {
  conversation_id: UUID;
  message_id: UUID;
  ticket_id: UUID | null;
  customer_id: UUID;
  channel: string;
  duplicate: boolean;
  workflow: Record<string, unknown> | null;
};

export type ConversationMessageCreate = {
  sender_type: "customer" | "agent" | "ai" | "system" | "internal_note";
  body: string;
  meta?: Record<string, unknown> | null;
};

export type UploadedConversationAttachment = {
  id: UUID;
  filename: string;
  content_type: string;
  size_bytes: number;
  scan_status: string;
};

export type ConversationContextTicket = ConversationDetailTicket & {
  conversation_id?: UUID;
  resolution_reason?: string | null;
};

export type ConversationSLATarget = {
  id: UUID;
  ticket_id: UUID;
  target_type: string;
  due_at: string;
  breached_at: string | null;
  status: string;
};

export type ConversationContext = {
  conversation: Omit<ConversationDetail, "messages" | "customer" | "ticket"> & Record<string, unknown>;
  recent_messages: ConversationDetailMessage[];
  customer: (ConversationDetailCustomer & Record<string, unknown>) | null;
  ticket: ConversationContextTicket | null;
  tags: ConversationTag[];
  insights: ConversationInsight[];
  latest_insight: ConversationInsight | null;
  suggested_actions: SuggestedAction[];
  workflow_executions: WorkflowExecution[];
  quality_reviews: Record<string, unknown>[];
  assignments: Record<string, unknown>[];
  sla: {
    violations: ConversationSLATarget[];
    open: ConversationSLATarget[];
    breached: ConversationSLATarget[];
  };
};

export type AutomationActivityCategory =
  | "conversation"
  | "ai_decision"
  | "workflow_execution"
  | "provider_call"
  | "approval"
  | "failure_retry"
  | "verification"
  | "repair"
  | "learned_insight";

export type AutomationActivityEvent = {
  id: string;
  category: AutomationActivityCategory;
  type: string;
  timestamp: string;
  title: string;
  description: string | null;
  status: string | null;
  actor_id: string | null;
  workflow_run_id: string | null;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown>;
};

export type AutomationActivity = {
  conversation_id: string;
  items: AutomationActivityEvent[];
  counts: Record<string, number>;
  has_more: boolean;
};

export type CustomerSummary = {
  customer_id: UUID;
  name: string | null;
  email: string | null;
  conversation_count: number;
  ticket_count: number;
  open_ticket_count: number;
  closed_ticket_count: number;
  channels: string[];
  first_seen_at: string | null;
  last_seen_at: string | null;
  latest_conversation_id: UUID | null;
  latest_ticket_id: UUID | null;
};

export type ReviewPlanOperation = {
  operation_type: string;
  operation_ref?: string | null;
  item_id?: string | null;
  item_label?: string | null;
  address?: Record<string, unknown> | null;
  approval_required?: boolean;
  execution_allowed?: boolean;
};

export type ReviewPlan = {
  status?: string;
  provider?: string;
  order_ref?: string | null;
  provider_order_id?: string | null;
  operations?: ReviewPlanOperation[];
  approval_required?: boolean;
  execution_allowed?: boolean;
};

export type ApprovalDecisionResult = {
  wait_id: string;
  status: string;
  workflow_run_id: string;
  resume_job_id: string | null;
  approved: boolean;
};
