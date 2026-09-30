import { useCallback } from "react";

import { createComposerBlock } from "../utils/createBlock";
import type {
  ComposerBlockKind,
  ComposerNode as ComposerNodeType,
} from "../types/composer";

type Props = {
  setNodes: (
    updater: (current: ComposerNodeType[]) => ComposerNodeType[],
  ) => void;
};

function nextPosition(currentLength: number) {
  return {
    x: 80 + currentLength * 56,
    y: 120 + currentLength * 34,
  };
}

export function useComposerBlockActions({
  setNodes,
}: Props) {
  const addBlock = useCallback((kind: ComposerBlockKind) => {
    setNodes((current) => [
      ...current,
      createComposerBlock(kind, nextPosition(current.length)),
    ]);
  }, [setNodes]);

  const addAgentBlock = useCallback((
    label: string,
    responsibility: string,
    saveAs: string,
    businessInputs: string[],
    businessOutputs: string[],
    tools: string[] = [],
    maxSteps = 5,
  ) => {
    setNodes((current) => [
      ...current,
      createComposerBlock(
        "ai_agent",
        nextPosition(current.length),
        {
          label,
          businessInputs,
          businessOutputs,
          config: {
            name: label,
            responsibility,
            save_as: saveAs,
            tools,
            max_steps: maxSteps,
          },
        },
      ),
    ]);
  }, [setNodes]);

  const addUnderstandRequest = useCallback(() => {
    addAgentBlock(
      "Understand Request",
      "Identify customer intent, urgency, order references, and what the customer needs next.",
      "request_understanding",
      ["Customer message"],
      ["Intent", "Urgency", "Next step"],
    );
  }, [addAgentBlock]);

  const addSummarizeConversation = useCallback(() => {
    addAgentBlock(
      "Summarize Conversation",
      "Create a concise internal summary of the customer conversation for agents and workflow decisions.",
      "conversation_summary",
      ["Conversation messages"],
      ["Summary"],
    );
  }, [addAgentBlock]);

  const addReviewRefund = useCallback(() => {
    addAgentBlock(
      "Review Refund",
      "Review refund eligibility, policy fit, order status, customer risk, and whether manager approval is needed.",
      "refund_review",
      ["Customer message", "Order context"],
      ["Refund decision", "Approval need"],
      ["shopify_get_order"],
      6,
    );
  }, [addAgentBlock]);

  const addAnalyzeSentiment = useCallback(() => {
    addAgentBlock(
      "Analyze Sentiment",
      "Detect customer sentiment, frustration, urgency, and escalation risk.",
      "sentiment_analysis",
      ["Customer message"],
      ["Sentiment", "Escalation risk"],
    );
  }, [addAgentBlock]);

  const addCustomAgent = useCallback(() => {
    addAgentBlock(
      "Custom Agent",
      "Describe exactly what this AI agent should do in this workflow.",
      "custom_agent_result",
      ["Workflow input"],
      ["Agent result"],
    );
  }, [addAgentBlock]);

  const addOrderSupportAgent = useCallback(() => {
    addAgentBlock(
      "Order Support Agent",
      `You are a world-class ecommerce customer support agent.

You receive:
- Customer message
- Shopify order information

Your job is to create a professional customer-facing response.

Rules:
- Never output JSON.
- Never expose internal fields.
- Never expose raw Shopify payloads.
- Write naturally and professionally.
- Use friendly support language.
- Explain order status clearly.
- Explain next steps clearly.

If order is paid but not fulfilled:
- Explain payment was received.
- Explain fulfillment has not happened yet.
- Explain tracking is unavailable until shipment.

If tracking exists:
- Show tracking number.
- Explain shipment status.

Output only the final customer reply.`,
      "order_support_reply",
      ["Customer message", "Shopify order"],
      ["Customer reply"],
      [],
      6,
    );
  }, [addAgentBlock]);

  const addShopifyOrderCheck = useCallback(() => {
    setNodes((current) => [
      ...current,
      createComposerBlock(
        "tool_action",
        nextPosition(current.length),
        {
          label: "Check Order",
          businessInputs: ["Order number", "Customer message"],
          businessOutputs: ["Order status", "Fulfillment status"],
          config: {
            name: "Check Order",
            action: "shopify_get_order",
            order_ref: "#1001",
            order_ref_from: "config",
            save_as: "shopify_order",
          },
        },
      ),
    ]);
  }, [setNodes]);

  const addTrackingCheck = useCallback(() => {
    setNodes((current) => [
      ...current,
      createComposerBlock(
        "tool_action",
        nextPosition(current.length),
        {
          label: "Check Shipping",
          businessInputs: ["Order context"],
          businessOutputs: ["Shipping status", "Tracking status"],
          config: {
            name: "Check Shipping",
            action: "shopify_shipping_status",
            order_ref_from: "last",
            save_as: "shipping_status",
          },
        },
      ),
    ]);
  }, [setNodes]);

  const addRefundOrder = useCallback(() => {
    setNodes((current) => [
      ...current,
      createComposerBlock(
        "tool_action",
        nextPosition(current.length),
        {
          label: "Refund Order",
          businessInputs: ["Order context", "Approval"],
          businessOutputs: ["Refund result"],
          config: {
            name: "Refund Order",
            action: "shopify_refund_order",
            order_ref_from: "vars",
            order_ref_key: "order_ref",
            reason: "Customer service workflow refund",
            save_as: "refund_result",
          },
        },
      ),
    ]);
  }, [setNodes]);

  const addCancelOrder = useCallback(() => {
    setNodes((current) => [
      ...current,
      createComposerBlock(
        "tool_action",
        nextPosition(current.length),
        {
          label: "Cancel Order",
          businessInputs: ["Order context", "Customer request"],
          businessOutputs: ["Cancellation result"],
          config: {
            name: "Cancel Order",
            action: "shopify_cancel_order",
            order_ref_from: "vars",
            order_ref_key: "order_ref",
            reason: "Customer service workflow cancellation",
            save_as: "cancel_result",
          },
        },
      ),
    ]);
  }, [setNodes]);

  const addSearchDocuments = useCallback(() => {
    setNodes((current) => [
      ...current,
      createComposerBlock(
        "knowledge_answer",
        nextPosition(current.length),
        {
          label: "Search Documents",
          businessInputs: ["Customer question"],
          businessOutputs: ["Document answer"],
          config: {
            query_from: "last",
            top_k: 5,
            save_as: "document_answer",
          },
        },
      ),
    ]);
  }, [setNodes]);

  const addSearchWeb = useCallback(() => {
    addAgentBlock(
      "Search Web",
      "Search external websites or public information sources and return useful answer context.",
      "web_search_result",
      ["Customer question"],
      ["Web answer"],
      ["web_search"],
      5,
    );
  }, [addAgentBlock]);

  const addTagConversation = useCallback(() => {
    setNodes((current) => [
      ...current,
      createComposerBlock(
        "ai_agent",
        nextPosition(current.length),
        {
          label: "Tag Conversation",
          businessInputs: ["Intent", "Urgency"],
          businessOutputs: ["Support tags"],
          config: {
            name: "Tag Conversation",
            responsibility:
              "Choose useful support tags such as refund, shipping_delay, VIP, damaged_item, or urgent.",
            save_as: "conversation_tags",
            tools: [],
            max_steps: 3,
          },
        },
      ),
    ]);
  }, [setNodes]);

  const addAssignAgent = useCallback(() => {
    setNodes((current) => [
      ...current,
      createComposerBlock(
        "ai_agent",
        nextPosition(current.length),
        {
          label: "Assign Agent",
          businessInputs: ["Intent", "Priority"],
          businessOutputs: ["Assigned owner"],
          config: {
            name: "Assign Agent",
            responsibility:
              "Decide which agent, team, or queue should own this conversation based on intent and urgency.",
            save_as: "assignment_decision",
            tools: [],
            max_steps: 3,
          },
        },
      ),
    ]);
  }, [setNodes]);

  return {
    addBlock,
    addUnderstandRequest,
    addSummarizeConversation,
    addReviewRefund,
    addAnalyzeSentiment,
    addCustomAgent,
    addOrderSupportAgent,
    addShopifyOrderCheck,
    addTrackingCheck,
    addRefundOrder,
    addCancelOrder,
    addSearchDocuments,
    addSearchWeb,
    addTagConversation,
    addAssignAgent,
  };
}
