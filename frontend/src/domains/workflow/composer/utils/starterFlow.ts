import { connectComposerBlocks } from "./connectBlocks";
import { createComposerBlock } from "./createBlock";
import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "../types/composer";

export function createStarterComposerFlow(): {
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
} {
  const trigger = createComposerBlock("customer_message_trigger", { x: 60, y: 160 }, {
    id: "starter-trigger",
    config: { input: "Where is my order #1001?" },
  });

  const order = createComposerBlock("shopify_check_order", { x: 280, y: 160 }, {
    id: "starter-order",
    config: { name: "Check Shopify order", save_as: "shopify_order" },
  });

  const agent = createComposerBlock("order_support_agent", { x: 520, y: 160 }, {
    id: "starter-agent",
    label: "Draft a helpful reply",
    config: { name: "Order Support Agent", save_as: "reply" },
  });

  const response = createComposerBlock(
    "send_response",
    { x: 760, y: 160 },
    {
      id: "starter-response",
      label: "Final Response",
    },
  );

  const nodes: ComposerNodeType[] = [trigger, order, agent, response];

  let edges: ComposerEdge[] = [];

  edges = connectComposerBlocks(
    {
      source: trigger.id,
      target: order.id,
      sourceHandle: null,
      targetHandle: null,
    },
    nodes,
    edges,
  );

  edges = connectComposerBlocks({
    source: order.id,
    target: agent.id,
    sourceHandle: null,
    targetHandle: null,
  }, nodes, edges);

  edges = connectComposerBlocks(
    {
      source: agent.id,
      target: response.id,
      sourceHandle: null,
      targetHandle: null,
    },
    nodes,
    edges,
  );

  return { nodes, edges };
}
