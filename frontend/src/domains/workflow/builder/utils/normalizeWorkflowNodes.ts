import type { Node } from "@xyflow/react";

type AgentRole =
    | "worker"
    | "decision"
    | "final"
    | "router"
    | "planner"
    | "evaluator"
    | "tool_executor"
    | "supervisor";

const CUSTOMER_CONTEXT_PROMPT =
    "You must use knowledge_search before answering when the tool is available.\n\n" +
    "Extract only structured facts.\n\n" +
    "Output format:\n" +
    "Customer facts:\n" +
    "- order_id:\n" +
    "- issue:\n" +
    "- customer_request:\n\n" +
    "Policy facts:\n" +
    "- exact policy rule found:\n\n" +
    "Do not suggest actions.\n" +
    "Do not ask questions.\n" +
    "Do not write customer-facing text.\n" +
    "Maximum 5 bullets total.";

const DECISION_PROMPT =
    "Decide the company action from the provided context.\n" +
    "Use policy facts as source of truth.\n" +
    "Output only the final internal decision/action.\n" +
    "Do not write customer-facing text.\n" +
    "Maximum 1 sentence.";

const FINAL_PROMPT =
    "Use the input as the source of truth.\n" +
    "Write only the final customer-facing response.\n" +
    "Do not mention internal approval.\n" +
    "Do not mention internal reasoning.\n" +
    "Do not ask more questions.\n" +
    "Be concise.";

function asData(node: Node): any {
    return { ...(node.data as any) };
}

function labelOf(data: any): string {
    return String(data.label ?? data.name ?? "").toLowerCase().trim();
}

function hasTool(data: any, toolName: string): boolean {
    return Array.isArray(data.tools) && data.tools.includes(toolName);
}

function ensureTool(data: any, toolName: string) {
    data.tools = Array.isArray(data.tools) ? data.tools : [];

    if (!hasTool(data, toolName)) {
        data.tools = [...data.tools, toolName];
    }
}

function normalizeNumber(value: unknown, fallback: number, max: number): number {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return fallback;
    return Math.min(n, max);
}
function normalizeOptionalNumber(value: unknown, fallback: number, max: number): number {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return fallback;
    return Math.min(n, max);
}


function isAgent(data: any): boolean {
    return data.nodeType === "agent.custom";
}

function isFinalAgent(data: any): boolean {
    const label = labelOf(data);

    return (
        isAgent(data) &&
        (data.role === "final" ||
            data.role === "final_writer" ||
            data.save_as === "final_answer_agent_result" ||
            label.includes("final answer") ||
            label.includes("final"))
    );
}

function isCustomerContextAgent(data: any): boolean {
    const label = labelOf(data);

    return (
        isAgent(data) &&
        (data.save_as === "customer_context_agent_result" ||
            label.includes("customer context") ||
            label.includes("context agent"))
    );
}

function isDecisionAgent(data: any): boolean {
    const label = labelOf(data);

    return (
        isAgent(data) &&
        (data.role === "decision" ||
            data.save_as === "decision_agent_result" ||
            label.includes("decision"))
    );
}

function normalizeBaseAgent(data: any) {
    data.backend = data.backend || "pure";
    data.pattern = data.pattern || "tool_agent";
    data.instruction = data.instruction || "";
    data.output_mode = data.output_mode || "text";
    data.context_keys = Array.isArray(data.context_keys) ? data.context_keys : [];
    data.tools = Array.isArray(data.tools) ? data.tools : [];
    data.role = (data.role || "worker") as AgentRole;
    data.max_steps = normalizeNumber(data.max_steps, 3, 8);
    data.max_output_chars = normalizeNumber(data.max_output_chars, 1000, 1200);
    data.token_budget_mode = data.token_budget_mode || "balanced";
    data.max_output_tokens = normalizeOptionalNumber(data.max_output_tokens, 220, 800);
}

function normalizeCustomerContextAgent(data: any) {
    data.role = "worker";
    data.input_from = data.input_from || "last";
    data.input_key = data.input_key || "input";
    data.save_as = data.save_as || "customer_context_agent_result";

    ensureTool(data, "knowledge_search");

    data.max_steps = 3;
    data.max_output_chars = 700;
    data.max_output_tokens = undefined;
    data.token_budget_mode = "balanced";
    data.system_prompt = CUSTOMER_CONTEXT_PROMPT;
}

function normalizeDecisionAgent(data: any) {
    data.role = "decision";
    data.input_from = "vars";
    data.input_key = data.input_key || "customer_context_agent_result";
    data.save_as = data.save_as || "decision_agent_result";

    data.max_steps = 3;
    data.max_output_chars = 500;
    data.max_output_tokens = 300;
    data.token_budget_mode = "lean";
    data.system_prompt = DECISION_PROMPT;
}

function normalizeFinalAgent(data: any) {
    data.role = "final";
    data.input_from = "vars";
    data.input_key = "decision_agent_result";
    data.save_as = "final_answer_agent_result";
    data.tools = [];

    data.max_steps = 3;
    data.max_output_chars = 600;
    data.max_output_tokens = 700;
    data.token_budget_mode = "balanced";

    data.output_mode = "text";
    data.context_keys = [];
    data.system_prompt = FINAL_PROMPT;
}

function normalizeHumanApproval(data: any) {
    data.name = data.name || "Human Approval";
    data.save_as = data.save_as || "approval_result";
    data.input_key = "resume_input";
    data.field = data.field || "approved";

    const question = String(data.question ?? "").trim();

    data.question =
        !question || question === "Approve refund?"
            ? "Approve this decision/action?"
            : question;
}

function normalizeJoin(data: any) {
    data.name = data.name || "Join Results";
    data.mode = data.mode || "object";
    data.save_as = data.save_as || "joined_result";
    data.separator = data.separator || "\n";
}

export function normalizeWorkflowNodes(nodes: Node[]): Node[] {
    return nodes.map((node) => {
        const data = asData(node);

        if (data.nodeType === "join.all") {
            normalizeJoin(data);
        }

        if (data.nodeType === "human.approval") {
            normalizeHumanApproval(data);
        }

        if (isAgent(data)) {
            normalizeBaseAgent(data);

            if (isCustomerContextAgent(data)) {
                normalizeCustomerContextAgent(data);
            }

            if (isDecisionAgent(data)) {
                normalizeDecisionAgent(data);
            }

            if (isFinalAgent(data)) {
                normalizeFinalAgent(data);
            }
        }

        return { ...node, data };
    });
}