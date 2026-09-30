import type { Edge, Node } from "@xyflow/react";

export function getConnectedAgentForTool(
    toolNodeId: string,
    nodes: Node[],
    edges: Edge[]
): { id: string; name: string } | null {
    const edge = edges.find((e) => e.source === toolNodeId);
    if (!edge) return null;

    const agent = nodes.find(
        (n) =>
            n.id === edge.target &&
            (n.data as any)?.nodeType === "agent.custom"
    );

    if (!agent) return null;

    const data = agent.data as any;

    return {
        id: agent.id,
        name: String(data.name ?? data.label ?? "AI Agent"),
    };
}