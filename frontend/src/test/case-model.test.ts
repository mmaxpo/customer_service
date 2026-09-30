import { describe, expect, it } from "vitest";

import type {
  AutomationActivityEvent,
  ConversationContext,
  ConversationDetail,
  SuggestedAction,
} from "@/domains/customer-service/model";
import {
  deriveCaseState,
  pickNextStep,
  suggestionCapability,
} from "@/domains/customer-service/inbox/case/caseState";
import { buildTimeline } from "@/domains/customer-service/inbox/case/timeline";
import { resolveOrderReference } from "@/domains/customer-service/inbox/utils/orderRef";

let seq = 0;
function event(partial: Partial<AutomationActivityEvent>): AutomationActivityEvent {
  seq += 1;
  return {
    id: `e${seq}`,
    category: "conversation",
    type: "message",
    timestamp: `2026-09-20T10:${String(seq).padStart(2, "0")}:00Z`,
    title: "",
    description: null,
    status: null,
    actor_id: null,
    workflow_run_id: null,
    entity_type: null,
    entity_id: null,
    details: {},
    ...partial,
  };
}

function suggestion(partial: Partial<SuggestedAction>): SuggestedAction {
  return {
    id: "s1",
    conversation_id: "c1",
    action_type: "shopify_refund",
    title: "Refund order",
    description: null,
    status: "suggested",
    confidence: 0.8,
    payload: { order_ref: "#1001" },
    created_at: "2026-09-20T10:00:00Z",
    ...partial,
  };
}

function conversation(senders: string[], status = "open"): ConversationDetail {
  return {
    id: "c1",
    customer_id: "u1",
    channel: "website",
    subject: null,
    status,
    created_at: "2026-09-20T10:00:00Z",
    updated_at: "2026-09-20T10:00:00Z",
    customer: { id: "u1", name: null, email: null, phone: null },
    ticket: null,
    messages: senders.map((sender, index) => ({
      id: `m${index}`,
      sender_type: sender,
      body: sender === "customer" ? "Where is order #2002?" : "Thanks",
      meta: null,
      created_at: "2026-09-20T10:00:00Z",
    })),
  };
}

function context(partial: Partial<ConversationContext> = {}): ConversationContext {
  return {
    conversation: {} as ConversationContext["conversation"],
    recent_messages: [],
    customer: null,
    ticket: { id: "t1", title: "", status: "open", priority: "normal", assigned_to: null, created_at: "", updated_at: "" },
    tags: [],
    insights: [],
    latest_insight: null,
    suggested_actions: [],
    workflow_executions: [],
    quality_reviews: [],
    assignments: [],
    sla: { violations: [], open: [], breached: [] },
    ...partial,
  };
}

describe("buildTimeline", () => {
  it("orders oldest first and maps message senders to actors", () => {
    const entries = buildTimeline([
      event({ type: "message", timestamp: "2026-09-20T10:05:00Z", description: "Reply", details: { sender_type: "ai" } }),
      event({ type: "message", timestamp: "2026-09-20T10:01:00Z", description: "Help", details: { sender_type: "customer" } }),
    ]);
    expect(entries.map((entry) => entry.kind === "message" && entry.actor)).toEqual(["customer", "tajeran"]);
  });

  it("collapses consecutive superseded suggestions into one entry", () => {
    const entries = buildTimeline([
      event({ type: "suggested_action", title: "Refund", details: { status: "superseded" } }),
      event({ type: "suggested_action", title: "Refund", details: { status: "superseded" } }),
      event({ type: "suggested_action", title: "Track order", details: { status: "suggested" } }),
    ]);
    expect(entries).toHaveLength(2);
    expect(entries[0].kind).toBe("collapsed");
  });

  it("hides duplicate audit rows and translates executed Shopify workflows", () => {
    const entries = buildTimeline([
      event({ type: "audit_log", title: "suggested_action.execution.started", details: { meta: {} } }),
      event({ type: "audit_log", title: "internal_note.created", details: { meta: {} } }),
      event({
        type: "audit_log",
        title: "suggested_action.executed",
        actor_id: "user-1",
        details: {
          meta: {
            action_type: "shopify_refund",
            execution_result: { mode: "workflow_started", shopify_action: "refund", order_ref: "#1001", requires_human_approval: true },
          },
        },
      }),
    ]);
    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({ kind: "event", actor: "teammate", title: "Started refund workflow for order #1001" });
  });

  it("groups runtime events under their workflow run", () => {
    const entries = buildTimeline([
      event({ type: "workflow_execution", title: "Refund workflow", status: "running", workflow_run_id: "r1" }),
      event({ type: "node", category: "provider_call", entity_type: "workflow_runtime_event", workflow_run_id: "r1", details: { node_type: "tool.shopify.order_lookup" } }),
    ]);
    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({ kind: "run", title: "Refund workflow" });
    expect(entries[0].kind === "run" && entries[0].steps[0].title).toBe("Shopify: order lookup");
  });
});

describe("case state and next step", () => {
  it("prefers a pending suggestion over the reply state", () => {
    const ctx = context({ suggested_actions: [suggestion({})] });
    const detail = conversation(["customer"]);
    expect(deriveCaseState(ctx, detail)?.label).toBe("Decision pending");
    expect(pickNextStep(ctx, detail)).toMatchObject({ kind: "suggestion" });
  });

  it("offers resolve only after the customer has the latest reply", () => {
    expect(pickNextStep(context(), conversation(["customer"]))).toBeNull();
    expect(pickNextStep(context(), conversation(["customer", "agent"]))).toMatchObject({ kind: "resolve", ticketId: "t1" });
  });

  it("reports resolved cases and offers no next step", () => {
    const ctx = context({ ticket: { ...context().ticket!, status: "RESOLVED" } });
    expect(deriveCaseState(ctx, conversation(["customer"]))?.label).toBe("Resolved");
    expect(pickNextStep(ctx, conversation(["customer"]))).toBeNull();
  });

  it("only executes suggestion types the backend can run with the data it has", () => {
    expect(suggestionCapability(suggestion({})).mode).toBe("execute");
    expect(suggestionCapability(suggestion({ action_type: "refund" })).mode).toBe("accept");
    expect(suggestionCapability(suggestion({ action_type: "assign", payload: {} })).mode).toBe("accept");
  });
});

describe("resolveOrderReference", () => {
  it("prefers insight entities, then suggestions, then message text", () => {
    const detail = conversation(["customer"]);
    expect(resolveOrderReference(context({
      latest_insight: { id: "i", conversation_id: "c1", intent: null, sentiment: null, urgency: null, summary: null, confidence: null, created_at: "", entities: { order_refs: ["#3003"] } },
      suggested_actions: [suggestion({})],
    }), detail)).toEqual({ ref: "#3003", source: "insight" });
    expect(resolveOrderReference(context({ suggested_actions: [suggestion({})] }), detail)).toEqual({ ref: "#1001", source: "suggestion" });
    expect(resolveOrderReference(context(), detail)).toEqual({ ref: "#2002", source: "message" });
  });
});
