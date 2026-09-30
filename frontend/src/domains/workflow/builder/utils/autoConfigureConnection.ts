import type { Connection, Edge, Node } from "@xyflow/react";

function nodeData(node: Node) {
    return node.data as any;
}

function outputKeyOf(node: Node): string {
    const d = nodeData(node);

    if (d.save_as) return String(d.save_as);
    if (d.nodeType === "trigger.message") return "input";
    if (d.nodeType === "agent.custom") return "agent_result";
    if (d.nodeType === "human.approval") return "approval_result";
    if (d.nodeType === "join.all") return "joined_result";

    return "last";
}

function makeSaveAs(label: string, fallback: string) {
    const key = label
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");

    return `${key || fallback}_result`;
}

function hasGenericSaveAs(value: unknown) {
    return !value || value === "agent_result" || value === "result";
}

function isFinalAgent(data: any) {
    const label = String(data.label ?? data.name ?? "").toLowerCase();

    return (
        data.role === "final" ||
        data.role === "final_writer" ||
        label.includes("final")
    );
}

function configureAgent(data: any, sourceData: any, sourceOutputKey: string) {
    const label = String(data.label ?? data.name ?? "Agent");
    const finalAgent = isFinalAgent(data);

    data.name = data.name || label;

    if (hasGenericSaveAs(data.save_as)) {
        data.save_as = makeSaveAs(label, "agent");
    }

    data.backend = data.backend || "pure";
    data.pattern = data.pattern || "tool_agent";
    data.instruction = data.instruction || "";
    data.output_mode = data.output_mode || "text";
    data.context_keys = Array.isArray(data.context_keys) ? data.context_keys : [];

    if (finalAgent) {
        data.role = "final";
        data.input_from = "vars";
        data.input_key = "decision_agent_result";
        data.tools = [];
        data.max_steps = 3;
        data.max_output_chars = 600;
        data.output_mode = "text";
        data.context_keys = [];
        data.system_prompt =
            "Use the input as the source of truth. Write only the final customer-facing response. Do not mention internal approval. Do not ask more questions. Be concise.";
    } else {
        data.role = data.role || "worker";
        data.tools = Array.isArray(data.tools) ? data.tools : [];
        data.max_steps = data.max_steps || 5;
        data.max_output_chars = data.max_output_chars || 1200;
        data.system_prompt =
            data.system_prompt ||
            "You are a helpful AI agent. Complete your responsibility using the available context and tools.";
    }

    if (sourceData.nodeType === "trigger.message") {
        data.input_from = "last";
        data.input_key = "input";
    } else if (sourceData.nodeType === "human.approval") {
        data.input_from = "vars";
        data.input_key = finalAgent ? "decision_agent_result" : sourceOutputKey;
    } else {
        data.input_from = "vars";
        data.input_key = sourceOutputKey;
    }
}

export function autoConfigureNodesOnConnect(
    nodes: Node[],
    connection: Connection
): Node[] {
    const source = nodes.find((n) => n.id === connection.source);
    const target = nodes.find((n) => n.id === connection.target);

    if (!source || !target) return nodes;

    const sourceData = nodeData(source);
    const targetData = nodeData(target);

    const sourceType = String(sourceData.nodeType ?? "");
    const targetType = String(targetData.nodeType ?? "");
    const sourceOutputKey = outputKeyOf(source);

    return nodes.map((node) => {
        if (node.id !== target.id) return node;

        const data = { ...(node.data as any) };

        if (sourceType === "tool.reference" && targetType === "agent.custom") {
            const toolName = String(sourceData.tool_name ?? "");
            const currentTools = Array.isArray(data.tools) ? data.tools : [];

            data.tools =
                toolName && !currentTools.includes(toolName)
                    ? [...currentTools, toolName]
                    : currentTools;

            configureAgent(data, { nodeType: "trigger.message" }, "input");

            return { ...node, data };
        }

        if (targetType === "agent.custom") {
            configureAgent(data, sourceData, sourceOutputKey);
        }

        if (targetType === "response") {
            data.name = data.name || "Final Response";
            data.answer_from = sourceOutputKey === "last" ? "last" : "vars";
            data.answer_key = sourceOutputKey;
            data.raw = Boolean(data.raw);
            data.from_var = data.from_var || "";
            data.as_json = Boolean(data.as_json);
        }

        if (targetType === "human.approval") {
            data.name = data.name || "Human Approval";
            data.save_as = data.save_as || "approval_result";
            data.question = data.question || "Approve this decision/action?";

            if (data.question === "Approve refund?") {
                data.question = "Approve this decision/action?";
            }

            data.input_key = "resume_input";
            data.field = data.field || "approved";
        }

        if (targetType === "set.variable") {
            data.name = data.name || "Set Value";
            data.save_as = data.save_as || sourceOutputKey;
        }

        if (targetType === "join.all") {
            data.name = data.name || "Join Results";
            data.save_as = data.save_as || "joined_result";
            data.mode = "object";
            data.separator = data.separator || "\n";
        }

        return { ...node, data };
    });
}

export function autoConfigureEdge(edge: Edge): Edge {
    return {
        ...edge,
        type: "gradient",
        animated: true,
        markerEnd: "url(#tajeran-edge-circle)",
        style: { strokeWidth: 2 },
    };
}