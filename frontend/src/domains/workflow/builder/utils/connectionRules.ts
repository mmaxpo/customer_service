import type { Connection, Edge, Node } from "@xyflow/react";

function nodeTypeOf(node?: Node | null) {
    return String((node?.data as any)?.nodeType ?? "");
}

export function validateWorkflowConnection(
    nodes: Node[],
    connection: Connection | Edge
): { ok: true } | { ok: false; reason: string } {
    const source = nodes.find((n) => n.id === connection.source);
    const target = nodes.find((n) => n.id === connection.target);

    const sourceType = nodeTypeOf(source);
    const targetType = nodeTypeOf(target);

    if (!source || !target) {
        return { ok: false, reason: "Missing source or target node." };
    }

    if (source.id === target.id) {
        return { ok: false, reason: "A node cannot connect to itself." };
    }

    if (sourceType === "tool.reference" && targetType === "agent.custom") {
        return { ok: true };
    }

    if (sourceType === "tool.reference") {
        return { ok: false, reason: "Tools can only connect into AI Agent nodes." };
    }

    if (targetType === "tool.reference") {
        return { ok: false, reason: "Tools are capabilities, not runtime steps. Connect Tool → AI Agent." };
    }

    if (sourceType === "trigger.message" && targetType === "response") {
        return { ok: false, reason: "A trigger should go through an agent or workflow step before response." };
    }

    if (targetType === "trigger.message") {
        return { ok: false, reason: "Trigger nodes cannot receive incoming connections." };
    }

    return { ok: true };
}