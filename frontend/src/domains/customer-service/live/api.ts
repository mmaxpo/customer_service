import { apiJson } from "@/platform/api/client";

const base = "/api/customer-service/studio/live";

export type Outcome = "answered" | "handed_over" | "failed" | "running" | "waiting_approval";

export type WaitingConversation = {
  conversation_id: string;
  customer_name: string | null;
  channel: string;
  last_customer_message: string;
  waiting_since: string;
  reason: string;
};

export type WaitingApproval = { id: string; run_id: string; question: string | null; created_at: string };

export type Problem = { reason: string; count: number; last_at: string; example_run_id: string | null };

export type LiveNow = {
  waiting_for_person: WaitingConversation[];
  approvals_waiting: WaitingApproval[];
  running: number;
  problems: Problem[];
};

export type ActivityRow = {
  run_id: string | null;
  conversation_id: string | null;
  created_at: string;
  attempts: number;
  channel: string | null;
  customer_message: string | null;
  workflow_id: string | null;
  workflow_name: string | null;
  version: number | null;
  outcome: Outcome;
  reason: string | null;
};

export const liveApi = {
  now: () => apiJson<LiveNow>(`${base}/now`),
  activity: (params: { days: number; outcome?: Outcome; workflowId?: string }) => {
    const query = new URLSearchParams({ days: String(params.days) });
    if (params.outcome) query.set("outcome", params.outcome);
    if (params.workflowId) query.set("workflow_id", params.workflowId);
    return apiJson<ActivityRow[]>(`${base}/activity?${query}`);
  },
};
