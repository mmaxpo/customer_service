import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";

export function createComposerFlowFromBackendWorkflow(
  workflow: Record<string, unknown> | null | undefined,
): {
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
} {
  const runtimeNodes = Array.isArray(workflow?.nodes)
    ? workflow.nodes
    : [];

  const runtimeEdges = Array.isArray(workflow?.edges)
    ? workflow.edges
    : [];

  const nodes: ComposerNodeType[] = runtimeNodes.map(
    (node: any, index: number) => {
      const nodeType = String(node?.data?.nodeType || "unknown.node");
      const isTrigger = nodeType === "trigger.message";
      const isApproval = nodeType === "human.approval";
      const isResponse = nodeType === "response";
      const isShopify = nodeType.startsWith("shopify.");

      return {
        id: String(node.id || `template-node-${index}`),
        type: "composer",
        position: node.position || { x: 120 + index * 280, y: 180 },
        data: {
          blockKind: isTrigger
            ? "customer_message_trigger"
            : isApproval
              ? "human_approval"
              : isResponse
                ? "send_response"
                : isShopify
                  ? "tool_action"
                  : "ai_agent",
          label:
            node.data?.name ||
            nodeType
              .replaceAll(".", " ")
              .replaceAll("_", " "),
          description: `Runtime node: ${nodeType}`,
          category: isTrigger
            ? "trigger"
            : isApproval
              ? "approval"
              : isResponse
                ? "response"
                : isShopify
                  ? "action"
                  : "agent",
          config: {
            ...node.data,
            nodeType,
          },
          runtime: {
            nodes: [node],
            edges: [],
          },
          advanced: true,
        },
      };
    },
  );

  const edges: ComposerEdge[] = runtimeEdges.map(
    (edge: any, index: number) => ({
      id: String(edge.id || `${edge.source}-${edge.target}-${index}`),
      source: String(edge.source),
      target: String(edge.target),
      sourceHandle: edge.sourceHandle ?? null,
      targetHandle: edge.targetHandle ?? null,
      data: {
        route: edge.route,
      },
    }),
  );

  return { nodes, edges };
}
