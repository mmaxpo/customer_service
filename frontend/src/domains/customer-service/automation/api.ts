import { apiJson, jsonBody } from "@/platform/api/client";

const base = "/api/customer-service/studio";

export type GraphNode = {
  id: string;
  type: string;
  label: string;
  type_title: string;
  category: string | null;
  risk: string | null;
};

export type GraphEdge = { source: string; target: string; condition: string | null };

export type Graph = { nodes: GraphNode[]; edges: GraphEdge[] };

export type StudioWorkflow = {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  live_version: number | null;
  dispatch_mode: "standard" | "exclusive" | "fallback";
  graph: Graph;
  runs_7d: number;
  answered_7d: number;
  edited_at: string;
  open_proposal_id: string | null;
  // A message must contain one of these for the workflow to run (empty = no keyword rule).
  keywords: string[];
  can_toggle: boolean;
};

// A workflow TCOS drafted from a prompt; nothing is saved until the owner saves it.
export type WorkflowDraft = {
  name: string;
  description: string;
  topic: string | null;
  keywords: string[];
  workflow: Record<string, unknown>;
  graph: Graph;
  validation_errors: string[];
};

export type StudioOverview = {
  workflows: StudioWorkflow[];
  routing: { messages_7d: number; unmatched_7d: number };
};

export type SummaryLine = { kind: "new" | "changed" | "same"; text: string };

export type RecentConversation = {
  run_id: string;
  conversation_id: string | null;
  status: string;
  created_at: string;
  customer_message: string | null;
  answer: string | null;
};

export type Proposal = {
  id: string;
  workflow_id: string;
  workflow_name: string;
  version: number;
  base_version: number;
  live_version: number | null;
  status: "draft" | "published" | "archived" | "discarded";
  requests: string[];
  summary: SummaryLine[];
  graph: Graph;
  base_graph: Graph;
  diff: { new: string[]; changed: string[]; removed: string[] };
  validation_errors: string[];
  recent_conversations: RecentConversation[];
  test_results: TestResults | null;
};

export type TestCase = RecentConversation & {
  draft_status: string | null;
  draft_error: string | null;
  draft_answer: string | null;
  fallback_used: boolean;
  blocked_steps: string[];
  provider_unavailable: boolean;
  passed: boolean;
  changed: boolean;
};

export type TestResults = {
  tested_at: string;
  total: number;
  passed: number;
  changed: number;
  untested: number;
  cases: TestCase[];
};

export type RawNode = { id: string; data: Record<string, unknown> & { nodeType: string; label?: string } };
export type RawEdge = { source: string; target: string; condition?: string | null };
export type RawWorkflow = { name?: string; nodes: RawNode[]; edges: RawEdge[] } & Record<string, unknown>;

export type WorkflowDetail = {
  id: string;
  name: string;
  live_version: number | null;
  workflow: RawWorkflow;
  open_proposal_id: string | null;
};

export type JsonSchemaProperty = {
  type?: string;
  anyOf?: { type?: string }[];
  enum?: unknown[];
  title?: string;
  description?: string;
  default?: unknown;
};

export type LibraryItem = {
  node_type: string;
  group: "agents" | "tools" | "logic";
  name: string;
  description: string;
  needs_approval: boolean;
  default_config: Record<string, unknown>;
  schema: { properties?: Record<string, JsonSchemaProperty>; required?: string[] };
};

export type WorkflowVersion = {
  id: string;
  version: number;
  status: "draft" | "published" | "archived";
  kind: "import" | "proposal" | null;
  note: string | null;
  summary: SummaryLine[];
  created_at: string;
  published_at: string | null;
};

export type VersionHistory = {
  workflow_id: string;
  workflow_name: string;
  live_version: number | null;
  versions: WorkflowVersion[];
};

export type ReviewReason = "flagged" | "failed" | "handed_over";

export type RunSummary = {
  run_id: string;
  conversation_id: string | null;
  status: string;
  workflow_id: string | null;
  workflow_name: string | null;
  version: number | null;
  created_at: string;
  customer_message: string | null;
  review_reasons: ReviewReason[];
};

export type RunStep = {
  node_id: string;
  status: "queued" | "running" | "done" | "skipped" | "error";
  started_at?: string;
  ended_at?: string;
  duration_ms?: number;
  output?: string | null;
  error?: string | null;
  reason?: string;
  meta?: Record<string, unknown>;
  problem?: "error" | "handoff_required" | null;
};

export type RunFlag = {
  id: string;
  run_id: string;
  step_id: string | null;
  message_id: string | null;
  note: string;
  created_at: string;
};

export type RunDetail = RunSummary & {
  failure: string | null;
  elapsed_sec: number | null;
  graph: Graph;
  steps: RunStep[];
  likely_cause: string | null;
  transcript: { id: string; sender: string; body: string; created_at: string }[];
  flags: RunFlag[];
};

export const studioApi = {
  overview: () => apiJson<StudioOverview>(`${base}/workflows`),

  createProposal: (workflowId: string, request: string) =>
    apiJson<Proposal>(`${base}/proposals`, {
      method: "POST",
      body: jsonBody({ workflow_id: workflowId, request }),
    }),

  draftWorkflow: (request: string) =>
    apiJson<WorkflowDraft>(`${base}/workflows/draft`, { method: "POST", body: jsonBody({ request }) }),

  createWorkflow: (draft: Pick<WorkflowDraft, "name" | "description" | "topic" | "keywords" | "workflow">) =>
    apiJson<{ workflow_id: string }>(`${base}/workflows`, { method: "POST", body: jsonBody(draft) }),

  setWorkflowEnabled: (id: string, enabled: boolean) =>
    apiJson(`${base}/workflows/${id}/enabled`, { method: "POST", body: jsonBody({ enabled }) }),

  setWorkflowKeywords: (id: string, keywords: string[]) =>
    apiJson(`${base}/workflows/${id}/keywords`, { method: "POST", body: jsonBody({ keywords }) }),

  deleteWorkflow: (id: string) => apiJson(`${base}/workflows/${id}`, { method: "DELETE" }),

  workflow: (id: string) => apiJson<WorkflowDetail>(`${base}/workflows/${id}`),

  versions: (id: string) => apiJson<VersionHistory>(`${base}/workflows/${id}/versions`),

  restoreVersion: (id: string, version: number) =>
    apiJson<{ workflow_id: string; live_version: number }>(`${base}/workflows/${id}/versions/${version}/restore`, {
      method: "POST",
    }),

  nodeLibrary: () => apiJson<LibraryItem[]>(`${base}/node-library`),

  proposeGraphEdit: (workflowId: string, workflow: RawWorkflow) =>
    apiJson<Proposal>(`${base}/proposals`, {
      method: "POST",
      body: jsonBody({ workflow_id: workflowId, workflow }),
    }),

  proposal: (id: string) => apiJson<Proposal>(`${base}/proposals/${id}`),

  refineProposal: (id: string, request: string) =>
    apiJson<Proposal>(`${base}/proposals/${id}/refine`, {
      method: "POST",
      body: jsonBody({ request }),
    }),

  testProposal: (id: string) => apiJson<TestResults>(`${base}/proposals/${id}/test`, { method: "POST" }),

  publishProposal: (id: string) =>
    apiJson<{ workflow_id: string; live_version: number }>(`${base}/proposals/${id}/publish`, {
      method: "POST",
    }),

  discardProposal: (id: string) => apiJson<void>(`${base}/proposals/${id}`, { method: "DELETE" }),

  reviewQueue: () => apiJson<RunSummary[]>(`${base}/review`),

  run: (id: string) => apiJson<RunDetail>(`${base}/runs/${id}`),

  flagRun: (id: string, payload: { note: string; step_id?: string | null; message_id?: string | null }) =>
    apiJson<{ id: string }>(`${base}/runs/${id}/flags`, {
      method: "POST",
      body: jsonBody(payload),
    }),

  dismissRun: (id: string) => apiJson<void>(`${base}/runs/${id}/dismiss`, { method: "POST" }),
};
