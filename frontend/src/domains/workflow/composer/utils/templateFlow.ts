import { connectComposerBlocks } from "./connectBlocks";
import { createComposerBlock } from "./createBlock";
import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "../types/composer";

export function createTemplateComposerFlow(
  template: string,
): {
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
} {
  const trigger = createComposerBlock(
    "customer_message_trigger",
    { x: 60, y: 180 },
    {
      id: `${template}-trigger`,
      config: {
        input:
          template === "refund"
            ? "Customer says: I received a damaged item. Please refund order #10482."
            : template === "order-status"
              ? "Customer says: Where is my order #10482?"
              : "Customer says: This is urgent. I need help with my order now.",
      },
    },
  );

  const firstAgent = createComposerBlock(
    "ai_agent",
    { x: 280, y: 180 },
    {
      id: `${template}-agent`,
      label:
        template === "refund"
          ? "Refund Triage Agent"
          : template === "order-status"
            ? "Order Status Agent"
            : "Urgency Classifier",
      config: {
        name:
          template === "refund"
            ? "Refund Triage Agent"
            : template === "order-status"
              ? "Order Status Agent"
              : "Urgency Classifier",
        responsibility:
          template === "refund"
            ? "Classify refund eligibility, inspect Shopify order context, detect damaged item risk, and decide if human approval is needed."
            : template === "order-status"
              ? "Use Shopify order context and shipping/tracking tools to explain order status clearly to the customer."
              : "Classify urgency, detect intent, and decide whether this should be routed to a specialist queue or handled automatically.",
        save_as:
          template === "refund"
            ? "refund_triage"
            : template === "order-status"
              ? "order_status_result"
              : "routing_decision",
        tools:
          template === "refund"
            ? ["shopify_get_order"]
            : template === "order-status"
              ? ["shopify_get_order", "shipping_track"]
              : [],
        max_steps: 6,
      },
    },
  );

  const maybeApproval =
    template === "refund"
      ? createComposerBlock(
          "human_approval",
          { x: 500, y: 180 },
          {
            id: `${template}-approval`,
            label: "Approve Refund",
            config: {
              question: "Approve this refund before executing?",
              save_as: "refund_approval",
            },
          },
        )
      : null;

  const refundAction =
    template === "refund"
      ? createComposerBlock("tool_action", { x: 720, y: 180 }, {
          id: `${template}-action`,
          label: "Execute approved refund",
          config: {
            name: "Execute approved refund",
            action: "shopify_refund_order",
            order_ref_from: "vars",
            order_ref_key: "order_ref",
            reason: "Approved customer-service refund",
            save_as: "refund_result",
          },
        })
      : null;

  const refundReplyAgent =
    template === "refund"
      ? createComposerBlock("ai_agent", { x: 940, y: 180 }, {
          id: `${template}-reply-agent`,
          label: "Write refund confirmation",
          config: {
            name: "Refund Confirmation Agent",
            responsibility: "Write a concise customer-facing confirmation using the approved refund result. Never claim success unless the refund result says it succeeded.",
            save_as: "refund_reply",
            tools: [],
            max_steps: 2,
          },
        })
      : null;

  const response = createComposerBlock(
    "send_response",
    { x: template === "refund" ? 720 : 500, y: 180 },
    {
      id: `${template}-response`,
      label:
        template === "refund"
          ? "Refund Reply"
          : template === "order-status"
            ? "Order Status Reply"
            : "Routing Reply",
      config: {
        answer_from: "vars",
        answer_key:
          template === "refund"
            ? "refund_triage"
            : template === "order-status"
              ? "order_status_result"
              : "routing_decision",
        as_json: false,
      },
    },
  );

  const nodes: ComposerNodeType[] = maybeApproval
    ? [trigger, firstAgent, maybeApproval, ...(refundAction ? [refundAction] : []), ...(refundReplyAgent ? [refundReplyAgent] : []), response]
    : [trigger, firstAgent, response];

  let edges: ComposerEdge[] = [];

  edges = connectComposerBlocks(
    {
      source: trigger.id,
      target: firstAgent.id,
      sourceHandle: null,
      targetHandle: null,
    },
    nodes,
    edges,
  );

  if (maybeApproval) {
    edges = connectComposerBlocks(
      {
        source: firstAgent.id,
        target: maybeApproval.id,
        sourceHandle: null,
        targetHandle: null,
      },
      nodes,
      edges,
    );

    if (refundAction && refundReplyAgent) {
      edges = connectComposerBlocks({
        source: maybeApproval.id,
        target: refundAction.id,
        sourceHandle: "approved",
        targetHandle: null,
      }, nodes, edges);
      edges = connectComposerBlocks({
        source: refundAction.id,
        target: refundReplyAgent.id,
        sourceHandle: null,
        targetHandle: null,
      }, nodes, edges);
      edges = connectComposerBlocks({
        source: refundReplyAgent.id,
        target: response.id,
        sourceHandle: null,
        targetHandle: null,
      }, nodes, edges);
    } else {
      edges = connectComposerBlocks(
      {
        source: maybeApproval.id,
        target: response.id,
        sourceHandle: "approved",
        targetHandle: null,
      },
      nodes,
      edges,
      );
    }
  } else {
    edges = connectComposerBlocks(
      {
        source: firstAgent.id,
        target: response.id,
        sourceHandle: null,
        targetHandle: null,
      },
      nodes,
      edges,
    );
  }

  return { nodes, edges };
}
