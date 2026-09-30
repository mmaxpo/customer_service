import type { Edge, Node } from "@xyflow/react";
import { normalizeRuntimeWorkflow } from "./normalizeRuntimeWorkflow";
import { normalizeWorkflowNodes } from "@/domains/workflow/builder/utils/normalizeWorkflowNodes";


export function getTriggerMessage(nodes: Node[]) {
    const trigger = nodes.find((n) => (n.data as any)?.nodeType === "trigger.message");
    return String((trigger?.data as any)?.input ?? "");
}

export function buildRuntimePayload(nodes: Node[], edges: Edge[]) {
    const message = getTriggerMessage(nodes);

    const runtimeNodes = nodes.filter(
        (node) => (node.data as any)?.nodeType !== "tool.reference"
    );

    const runtimeNodeIds = new Set(runtimeNodes.map((node) => node.id));

    const runtimeEdges = edges.filter(
        (edge) => runtimeNodeIds.has(edge.source) && runtimeNodeIds.has(edge.target)
    );

    const normalizedNodes = normalizeWorkflowNodes(runtimeNodes);
    const normalized = normalizeRuntimeWorkflow(normalizedNodes, runtimeEdges);

    return {
        workflow: normalized,
        message,
        thread_id: "runtime-preview",
        strict: true,
    };
}