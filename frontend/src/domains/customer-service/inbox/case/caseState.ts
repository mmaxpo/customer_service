import type {
  ConversationContext,
  ConversationDetail,
  SuggestedAction,
  WorkflowExecution,
} from "@/domains/customer-service/model";

import { lower } from "./format";
import type { Tone } from "./timeline";

const FAILED = new Set(["failed", "dead_letter", "error"]);
const CLOSED = new Set(["resolved", "closed"]);
const VISIBLE_SENDERS = new Set(["customer", "agent", "ai"]);

export type CaseState = { label: string; tone: Tone; description: string };

function newestExecution(executions: WorkflowExecution[]) {
  return [...executions].sort(
    (a, b) => Date.parse(b.created_at ?? "") - Date.parse(a.created_at ?? ""),
  )[0];
}

export function lastVisibleSender(conversation: ConversationDetail | null) {
  const messages = conversation?.messages ?? [];
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const sender = lower(messages[index].sender_type);
    if (VISIBLE_SENDERS.has(sender)) return sender;
  }
  return null;
}

export function pendingSuggestions(context: ConversationContext | null) {
  return (context?.suggested_actions ?? [])
    .filter((action) => lower(action.status) === "suggested")
    .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0) || Date.parse(b.created_at) - Date.parse(a.created_at));
}

export function isCaseClosed(context: ConversationContext | null, conversation: ConversationDetail | null) {
  return CLOSED.has(lower(context?.ticket?.status)) || CLOSED.has(lower(conversation?.status));
}

// The newest run finished but a step asked for a person (e.g. the AI provider
// was down and the customer got the standby reply), and no teammate has replied since.
export function handedOverExecution(context: ConversationContext | null, conversation: ConversationDetail | null) {
  const latest = newestExecution(context?.workflow_executions ?? []);
  return latest?.handed_over && lastVisibleSender(conversation) !== "agent" ? latest : null;
}

export function waitingApprovalExecution(context: ConversationContext | null) {
  const latest = newestExecution(context?.workflow_executions ?? []);
  return latest?.waiting_approval ? latest : null;
}

export function failedExecution(context: ConversationContext | null) {
  const latest = newestExecution(context?.workflow_executions ?? []);
  return latest && FAILED.has(lower(latest.status)) ? latest : null;
}

// One current state for the header, from real case data only. Case-linked approvals
// are not derivable until the backend links suggestion workflows to conversations (G1).
export function deriveCaseState(
  context: ConversationContext | null,
  conversation: ConversationDetail | null,
): CaseState | null {
  if (!context || !conversation) return null;

  if (isCaseClosed(context, conversation)) {
    return { label: "Resolved", tone: "neutral", description: "The ticket for this case is resolved." };
  }
  if (failedExecution(context)) {
    return { label: "Action failed", tone: "failure", description: "The latest workflow for this case failed." };
  }
  if (handedOverExecution(context, conversation)) {
    return {
      label: "Needs a person",
      tone: "attention",
      description: "The workflow couldn't answer and handed this case to your team.",
    };
  }
  if (waitingApprovalExecution(context)) {
    return {
      label: "Waiting for approval",
      tone: "attention",
      description: "The workflow is paused until someone approves it in Approvals.",
    };
  }
  const pending = pendingSuggestions(context);
  if (pending.length > 0) {
    return {
      label: "Decision pending",
      tone: "attention",
      description: `Tajeran suggested ${pending.length === 1 ? "an action" : `${pending.length} actions`} that need a decision.`,
    };
  }
  const sender = lastVisibleSender(conversation);
  if (sender === "customer") {
    return { label: "Customer waiting", tone: "attention", description: "The customer sent the latest message." };
  }
  if (sender === "agent" || sender === "ai") {
    return { label: "Replied", tone: "neutral", description: "The customer has the latest reply." };
  }
  return { label: "Open", tone: "neutral", description: "This case is open." };
}

export type SuggestionCapability =
  | { mode: "execute"; label: string; confirm: string | null }
  | { mode: "accept"; reason: string };

// What the inbox can truthfully do with a suggestion, based on how the backend executes it.
export function suggestionCapability(action: SuggestedAction): SuggestionCapability {
  const orderRef = typeof action.payload?.order_ref === "string" ? action.payload.order_ref : null;
  const forOrder = orderRef ? ` for order ${orderRef}` : "";

  switch (action.action_type) {
    case "shopify_track_order":
      return { mode: "execute", label: "Check shipping status", confirm: null };
    case "shopify_refund":
      return {
        mode: "execute",
        label: "Start refund approval",
        confirm: `This starts the Shopify refund workflow${forOrder}. Nothing is refunded until someone approves it.`,
      };
    case "shopify_cancel":
      return {
        mode: "execute",
        label: "Start cancellation approval",
        confirm: `This starts the Shopify cancellation workflow${forOrder}. The order isn't cancelled until someone approves it.`,
      };
    case "shopify_damaged_item":
      return {
        mode: "execute",
        label: "Start damaged-item workflow",
        confirm: `This starts the Shopify damaged-item workflow${forOrder}. Changes to the order need approval.`,
      };
    case "close_ticket":
      return { mode: "execute", label: "Close ticket", confirm: null };
    case "escalate":
      return { mode: "execute", label: "Escalate", confirm: null };
    case "reply":
      return typeof action.payload?.body === "string" && action.payload.body.trim()
        ? { mode: "execute", label: "Send suggested reply", confirm: null }
        : { mode: "accept", reason: "This suggestion has no reply text to send." };
    case "assign":
      return typeof action.payload?.assigned_to === "string"
        ? { mode: "execute", label: "Assign", confirm: null }
        : { mode: "accept", reason: "This suggestion doesn't say who to assign." };
    case "refund":
      return { mode: "accept", reason: "Refunds run through the Shopify refund workflow, which needs an order-linked suggestion." };
    default:
      return { mode: "accept", reason: "The inbox can't carry out this suggestion directly." };
  }
}

export type NextStep =
  | { kind: "failed"; execution: WorkflowExecution }
  | { kind: "suggestion"; action: SuggestedAction; more: number }
  | { kind: "resolve"; ticketId: string };

export function pickNextStep(
  context: ConversationContext | null,
  conversation: ConversationDetail | null,
): NextStep | null {
  if (!context || !conversation || isCaseClosed(context, conversation)) return null;

  const failed = failedExecution(context);
  if (failed) return { kind: "failed", execution: failed };

  const pending = pendingSuggestions(context);
  if (pending.length > 0) return { kind: "suggestion", action: pending[0], more: pending.length - 1 };

  // A handed-over or approval-waiting case needs the team, not closing.
  if (handedOverExecution(context, conversation) || waitingApprovalExecution(context)) return null;

  const sender = lastVisibleSender(conversation);
  if ((sender === "agent" || sender === "ai") && context.ticket) {
    return { kind: "resolve", ticketId: context.ticket.id };
  }
  return null;
}
