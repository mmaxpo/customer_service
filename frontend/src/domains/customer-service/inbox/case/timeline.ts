import type { AutomationActivityEvent } from "@/domains/customer-service/model";

import { humanize, lower } from "./format";

export type Actor = "customer" | "teammate" | "tajeran" | "workflow" | "system";
export type Tone = "neutral" | "attention" | "failure" | "commerce";

export type Evidence = { label: string; value: string };

export type TimelineMessage = {
  kind: "message";
  id: string;
  at: string;
  actor: Actor;
  body: string;
  aiAssisted: boolean;
};

export type TimelineNote = { kind: "note"; id: string; at: string; body: string };

export type TimelineEvent = {
  kind: "event";
  id: string;
  at: string;
  actor: Actor;
  title: string;
  detail?: string | null;
  status?: { label: string; tone: Tone; running?: boolean } | null;
  evidence?: Evidence[];
};

export type TimelineCollapsed = {
  kind: "collapsed";
  id: string;
  at: string;
  title: string;
  events: TimelineEvent[];
};

export type TimelineRun = {
  kind: "run";
  id: string;
  at: string;
  runId: string;
  title: string;
  status: TimelineEvent["status"];
  steps: TimelineEvent[];
};

export type TimelineEntry = TimelineMessage | TimelineNote | TimelineEvent | TimelineCollapsed | TimelineRun;

type Details = Record<string, unknown>;

const asRecord = (value: unknown): Details =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Details) : {};
const asString = (value: unknown): string | null =>
  typeof value === "string" && value.trim() ? value.trim() : null;
const asStrings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && !!item.trim()) : [];

function executionStatus(status: string | null | undefined): TimelineEvent["status"] {
  const value = lower(status);
  if (!value) return null;
  if (["failed", "dead_letter", "error", "cancelled"].includes(value)) return { label: humanize(value), tone: "failure" };
  if (["queued", "running", "processing", "pending"].includes(value)) return { label: humanize(value), tone: "neutral", running: true };
  if (["paused", "waiting"].includes(value)) return { label: "Waiting", tone: "attention" };
  return { label: humanize(value), tone: "neutral" };
}

const SUGGESTION_STATUS: Record<string, { label: string; tone: Tone }> = {
  suggested: { label: "Awaiting decision", tone: "attention" },
  accepted: { label: "Accepted", tone: "neutral" },
  executed: { label: "Done", tone: "neutral" },
  rejected: { label: "Dismissed", tone: "neutral" },
  superseded: { label: "Replaced", tone: "neutral" },
};

export function autopilotEvidence(payload: Details): Evidence[] {
  const evidence: Evidence[] = [];
  const reason = asString(payload.reason);
  if (reason) evidence.push({ label: "Reason", value: reason });
  const orderRef = asString(payload.order_ref);
  if (orderRef) evidence.push({ label: "Order", value: orderRef });

  const autopilot = asRecord(payload.autopilot);
  if (autopilot.requires_approval === true) evidence.push({ label: "Approval", value: "Required before execution" });
  const risk = asString(autopilot.risk);
  if (risk) evidence.push({ label: "Risk", value: humanize(risk) });
  const decision = asString(autopilot.decision);
  if (decision) evidence.push({ label: "Automation policy", value: humanize(decision) });
  const codes = asStrings(autopilot.reason_codes);
  if (codes.length) evidence.push({ label: "Policy checks", value: codes.map(humanize).join(", ") });
  return evidence;
}

function insightEvent(item: AutomationActivityEvent): TimelineEvent {
  const d = item.details;
  const intent = asString(d.intent) ?? asString(item.description);
  const evidence: Evidence[] = [];
  const urgency = asString(d.urgency);
  if (urgency) evidence.push({ label: "Urgency", value: humanize(urgency) });
  const sentiment = asString(d.sentiment);
  if (sentiment) evidence.push({ label: "Sentiment", value: humanize(sentiment) });
  const entities = asRecord(d.entities);
  const orders = asStrings(entities.order_refs);
  if (orders.length) evidence.push({ label: "Orders mentioned", value: orders.join(", ") });
  const products = asStrings(entities.products);
  if (products.length) evidence.push({ label: "Products", value: products.join(", ") });
  const confidence = typeof d.confidence === "number" ? d.confidence : null;
  if (confidence !== null && confidence < 0.6) evidence.push({ label: "Confidence", value: "Low, worth checking" });
  const fallback = asString(d.fallback_reason);
  if (fallback) evidence.push({ label: "Analysis", value: `Fallback used (${humanize(fallback)})` });

  return {
    kind: "event",
    id: item.id,
    at: item.timestamp,
    actor: "tajeran",
    title: intent ? `Understood the request: ${humanize(intent).toLowerCase()}` : "Analysed the conversation",
    detail: asString(d.summary),
    evidence,
  };
}

function suggestionEvent(item: AutomationActivityEvent): TimelineEvent {
  const d = item.details;
  const status = lower(asString(d.status));
  return {
    kind: "event",
    id: item.id,
    at: item.timestamp,
    actor: "tajeran",
    title: `Suggested: ${item.title}`,
    detail: item.description,
    status: SUGGESTION_STATUS[status] ?? (status ? { label: humanize(status), tone: "neutral" } : null),
    evidence: autopilotEvidence(asRecord(d.payload)),
  };
}

function executedTitle(result: Details, actionType: string | null): { title: string; evidence: Evidence[] } {
  const evidence: Evidence[] = [];
  const orderRef = asString(result.order_ref);
  const type = asString(result.type) ?? actionType;

  if (result.mode === "workflow_started") {
    const action = asString(result.shopify_action);
    if (result.requires_human_approval === true) evidence.push({ label: "Approval", value: "Required before Shopify changes" });
    return {
      title: `Started ${action ? humanize(action).toLowerCase() : "a"} workflow${orderRef ? ` for order ${orderRef}` : ""}`,
      evidence,
    };
  }

  switch (type) {
    case "shopify_track_order":
      return { title: `Checked shipping status${orderRef ? ` for order ${orderRef}` : ""}`, evidence };
    case "assign":
      return { title: "Assigned the case", evidence };
    case "apply_tag":
      return { title: `Tagged ${asString(result.tag) ?? "the case"}`, evidence };
    case "reply":
      return { title: "Sent the suggested reply", evidence };
    case "close_ticket":
      return { title: "Closed the ticket", evidence };
    case "escalate":
      return { title: "Escalated the case", evidence };
    case "send_macro":
      return { title: "Sent a macro", evidence };
    default:
      return { title: `Carried out: ${humanize(type ?? "suggested action").toLowerCase()}`, evidence };
  }
}

const HIDDEN_AUDIT = new Set([
  "suggested_action.execution.started",
  "internal_note.created",
  "ticket.assigned",
]);

function auditEvent(item: AutomationActivityEvent): TimelineEvent | null {
  const action = item.title;
  if (HIDDEN_AUDIT.has(action)) return null;

  const meta = asRecord(item.details.meta);
  const actor: Actor = item.actor_id ? "teammate" : "system";
  const actionType = asString(meta.action_type);

  if (action === "suggested_action.execution.completed") {
    const status = lower(asString(meta.status));
    if (!status.includes("fail")) return null;
    return {
      kind: "event", id: item.id, at: item.timestamp, actor: "system",
      title: `Could not carry out: ${humanize(actionType ?? "suggested action").toLowerCase()}`,
      status: { label: "Failed", tone: "failure" },
    };
  }

  if (action === "suggested_action.accepted") {
    return {
      kind: "event", id: item.id, at: item.timestamp, actor,
      title: `Accepted the suggestion${actionType ? `: ${humanize(actionType).toLowerCase()}` : ""}`,
    };
  }

  if (action === "suggested_action.executed") {
    const { title, evidence } = executedTitle(asRecord(meta.execution_result), actionType);
    return { kind: "event", id: item.id, at: item.timestamp, actor, title, evidence };
  }

  if (action.startsWith("autopilot.")) {
    return {
      kind: "event", id: item.id, at: item.timestamp, actor: "tajeran",
      title: `Automation policy: ${humanize(action.slice("autopilot.".length)).toLowerCase()}`,
      detail: item.description,
    };
  }

  return {
    kind: "event", id: item.id, at: item.timestamp, actor,
    title: humanize(action),
    detail: item.description,
  };
}

function runtimeStep(item: AutomationActivityEvent): TimelineEvent {
  const node = asString(item.details.node_type) ?? item.type;
  const nodeLabel = humanize(node.replace(/^(tool|node|capability)\./, "")).toLowerCase();
  const labels: Record<string, string> = {
    provider_call: node.includes("shopify") ? `Shopify: ${nodeLabel.replace(/^shopify\s*/, "")}` : `Called ${nodeLabel}`,
    approval: "Paused for human approval",
    verification: "Verified the result",
    failure_retry: `Step failed: ${nodeLabel}`,
    repair: "Adjusted the plan",
    learned_insight: "Recorded a learning",
    ai_decision: `Decided: ${nodeLabel}`,
  };

  return {
    kind: "event",
    id: item.id,
    at: item.timestamp,
    actor: "workflow",
    title: labels[item.category] ?? humanize(nodeLabel),
    detail: item.description,
    status: item.category === "failure_retry" ? { label: "Failed", tone: "failure" } : executionStatus(item.status),
  };
}

function toEntry(item: AutomationActivityEvent): TimelineEntry | null {
  const d = item.details;

  switch (item.type) {
    case "message": {
      const sender = lower(asString(d.sender_type));
      const meta = asRecord(d.meta);
      const actor: Actor =
        sender === "customer" ? "customer" : sender === "agent" ? "teammate" : sender === "ai" ? "tajeran" : "system";
      return {
        kind: "message", id: item.id, at: item.timestamp, actor,
        body: item.description ?? "", aiAssisted: meta.ai_assisted === true,
      };
    }
    case "internal_note":
      return { kind: "note", id: item.id, at: item.timestamp, body: item.description ?? "" };
    case "tag_added":
      return { kind: "event", id: item.id, at: item.timestamp, actor: "system", title: `Tagged ${item.description ?? ""}`.trim() };
    case "ticket_assigned":
      return { kind: "event", id: item.id, at: item.timestamp, actor: item.actor_id ? "teammate" : "system", title: "Assigned the case", detail: item.description };
    case "insight_generated":
      return insightEvent(item);
    case "suggested_action":
      return suggestionEvent(item);
    case "audit_log":
      return auditEvent(item);
    case "sla_target":
      return { kind: "event", id: item.id, at: item.timestamp, actor: "system", title: "Response target set", detail: item.description };
    case "sla_breached":
      return { kind: "event", id: item.id, at: item.timestamp, actor: "system", title: "Response target missed", status: { label: "Breached", tone: "failure" } };
    case "quality_review":
      return { kind: "event", id: item.id, at: item.timestamp, actor: "system", title: "Quality review completed", detail: item.description };
    default:
      return { kind: "event", id: item.id, at: item.timestamp, actor: "system", title: humanize(item.title), detail: item.description };
  }
}

// Builds the chronological case story (oldest first) from automation activity.
export function buildTimeline(items: AutomationActivityEvent[]): TimelineEntry[] {
  const chronological = [...items].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  const runs = new Map<string, TimelineRun>();
  const entries: TimelineEntry[] = [];

  for (const item of chronological) {
    const runId = item.workflow_run_id;
    const isRuntime = item.entity_type === "workflow_runtime_event";

    if (runId && (isRuntime || item.type === "workflow_execution")) {
      let run = runs.get(runId);
      if (!run) {
        run = { kind: "run", id: `run:${runId}`, at: item.timestamp, runId, title: "Workflow", status: null, steps: [] };
        runs.set(runId, run);
        entries.push(run);
      }
      if (item.type === "workflow_execution") {
        run.title = item.title;
        run.status = executionStatus(item.status);
      } else {
        run.steps.push(runtimeStep(item));
      }
      continue;
    }

    if (item.type === "workflow_execution") {
      entries.push({
        kind: "event", id: item.id, at: item.timestamp, actor: "workflow",
        title: `Workflow: ${item.title}`, detail: item.description, status: executionStatus(item.status),
      });
      continue;
    }

    const entry = toEntry(item);
    if (entry) entries.push(entry);
  }

  return collapseSuperseded(entries);
}

function isSuperseded(entry: TimelineEntry): entry is TimelineEvent {
  return entry.kind === "event" && entry.status?.label === SUGGESTION_STATUS.superseded.label && entry.title.startsWith("Suggested:");
}

function collapseSuperseded(entries: TimelineEntry[]): TimelineEntry[] {
  const result: TimelineEntry[] = [];
  let buffer: TimelineEvent[] = [];

  const flush = () => {
    if (buffer.length === 0) return;
    if (buffer.length === 1) {
      result.push(buffer[0]);
    } else {
      result.push({
        kind: "collapsed",
        id: `collapsed:${buffer[0].id}`,
        at: buffer[buffer.length - 1].at,
        title: `${buffer.length} earlier suggestions were replaced by newer ones`,
        events: buffer,
      });
    }
    buffer = [];
  };

  for (const entry of entries) {
    if (isSuperseded(entry)) {
      buffer.push(entry);
    } else {
      flush();
      result.push(entry);
    }
  }
  flush();
  return result;
}
