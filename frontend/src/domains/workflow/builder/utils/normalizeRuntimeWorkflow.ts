import type { Edge, Node } from "@xyflow/react";

function dataOf(node: Node) {
    return node.data as any;
}

function slug(value: string, fallback: string) {
    const s = value
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");

    return s || fallback;
}

function stableSaveAs(node: Node, used: Set<string>) {
    const d = dataOf(node);
    const label = String(d.name ?? d.label ?? d.nodeType ?? "node");
    const base = `${slug(label, "node")}_result`;

    let candidate = base;
    let i = 2;

    while (used.has(candidate)) {
        candidate = `${base}_${i}`;
        i += 1;
    }

    used.add(candidate);
    return candidate;
}

function isGenericSaveAs(value: unknown) {
    return (
        !value ||
        value === "agent_result" ||
        value === "bot_custom_agent_result" ||
        value === "result"
    );
}

function outputKeyOf(node: Node) {
    const d = dataOf(node);

    if (d.save_as) return String(d.save_as);
    if (d.nodeType === "trigger.message") return "input";
    if (d.nodeType === "join.all") return "joined_result";
    if (d.nodeType === "human.approval") return "approval_result";

    return "last";
}

function isFinalAgentData(d: any) {
    const label = String(d.label ?? d.name ?? "").toLowerCase();

    return (
        d.nodeType === "agent.custom" &&
        (
            d.role === "final" ||
            d.save_as === "final_answer_agent_result" ||
            label.includes("final answer") ||
            label.includes("final")
        )
    );
}



export function normalizeRuntimeWorkflow(nodes: Node[], edges: Edge[]) {
    const used = new Set<string>();

    const normalizedNodes = nodes.map((node) => {
        const d = { ...(node.data as any) };

        if (d.nodeType === "agent.custom") {
            if (isGenericSaveAs(d.save_as)) {
                d.save_as = stableSaveAs({ ...node, data: d }, used);
            } else {
                used.add(String(d.save_as));
            }

            d.backend = d.backend || "pure";
            d.pattern = d.pattern || "tool_agent";
            d.input_from = d.input_from || "last";
            d.input_key = d.input_key || "input";
            d.tools = Array.isArray(d.tools) ? d.tools : [];
            d.max_steps = d.max_steps || 5;
        }

        if (d.nodeType === "join.all") {
            d.name = d.name || "Join Results";
            d.save_as = d.save_as || "joined_result";
            used.add(String(d.save_as));
        }

        if (d.nodeType === "human.approval") {
            d.name = d.name || "Human Approval";
            d.save_as = d.save_as || "approval_result";
            d.field = d.field || "approved";
            used.add(String(d.save_as));
        }

        return { ...node, data: d };
    });

    const byId = new Map(normalizedNodes.map((n) => [n.id, n]));

    const finalNodes = normalizedNodes.map((node) => {
        const d = { ...(node.data as any) };
        const incoming = edges.filter((e) => e.target === node.id);
        const firstParent = incoming[0] ? byId.get(incoming[0].source) : null;

        if (d.nodeType === "agent.custom" && firstParent && !isFinalAgentData(d)) {
            const parentData = dataOf(firstParent);

            if (parentData.nodeType === "trigger.message") {
                d.input_from = "last";
                d.input_key = "input";
            } else {
                d.input_from = "vars";
                d.input_key = outputKeyOf(firstParent);
            }
        }
        if (isFinalAgentData(d)) {
            d.role = "final";
            d.input_from = "vars";
            d.input_key = "decision_agent_result";
            d.save_as = "final_answer_agent_result";
            d.tools = [];
            d.max_steps = 3;
            d.max_output_chars = 600;
            d.max_output_tokens = 300;
            d.token_budget_mode = "cheap";
        }
        if (d.nodeType === "human.approval") {
            d.input_key = "resume_input";
            d.save_as = d.save_as || "approval_result";
            d.field = d.field || "approved";
        }

        if (d.nodeType === "response" && firstParent) {
            d.answer_from = "vars";
            d.answer_key = outputKeyOf(firstParent);
            d.raw = Boolean(d.raw);
            d.from_var = d.from_var || "";
            d.as_json = Boolean(d.as_json);
        }

        return { ...node, data: d };
    });

    return {
        nodes: finalNodes,
        edges,
    };
}