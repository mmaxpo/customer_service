import type { ComposerBlockDefinition } from "../types/composer";

export const BLOCK_DEFINITIONS: ComposerBlockDefinition[] = [
    {
        kind: "customer_message_trigger",
        label: "Customer Message",
        description: "Starts when a customer sends a message.",
        category: "trigger",
        icon: "message-circle",
        ports: [{ id: "out", label: "Message", kind: "output" }],

        businessInputs: [],
        businessOutputs: ["Customer message"],
        defaultConfig: {
            input: "Customer asks for help...",
        },
        runtimeNodeTypes: ["trigger.message"],
    },
    {
        kind: "ai_agent",
        label: "Analyze Request",
        description: "Understands the customer message, checks context, and decides the next best step.",
        category: "agent",
        icon: "bot",
        ports: [
            { id: "in", label: "Input", kind: "input" },
            { id: "out", label: "Result", kind: "output" },
        ],
        defaultConfig: {
            name: "Analyze Request",
            responsibility: "Understand what the customer needs, check available context, and produce a clear decision for the workflow.",
            save_as: "agent_result",
            backend: "pure",
            pattern: "tool_agent",
            tools: [],
            max_steps: 5,
        },
        businessInputs: [
            "Customer message"
        ],
        businessOutputs: [
            "Intent",
            "Decision"
        ],

        runtimeNodeTypes: ["agent.custom"],
    },
    {
        kind: "parallel_agents",
        label: "Check Multiple Signals",
        description: "Checks policy, customer context, and risk at the same time before continuing.",
        category: "group",
        icon: "git-branch",
        ports: [
            { id: "in", label: "Input", kind: "input" },
            { id: "out", label: "Joined Result", kind: "output" },
        ],
        defaultConfig: {
            agents: [
                { name: "Policy Agent", responsibility: "Check the policy." },
                { name: "Customer Agent", responsibility: "Check customer context." },
                { name: "Risk Agent", responsibility: "Check risk or fraud signals." },
            ],
            output_key: "parallel_result",
        },
        businessInputs: [
            "Customer message",
            "Policy context"
        ],
        businessOutputs: [
            "Risk check",
            "Joined decision"
        ],

        runtimeNodeTypes: ["agent.custom", "join.all"],
    },
    {
        kind: "human_approval",
        label: "Manager Approval",
        description: "Pauses the automation until a manager approves or rejects the next action.",
        category: "approval",
        icon: "shield-check",
        ports: [
            { id: "in", label: "Request", kind: "input" },
            { id: "approved", label: "Approved", kind: "output" },
            { id: "rejected", label: "Rejected", kind: "output" },
        ],
        defaultConfig: {
            question: "Should a manager approve this customer-service action?",
            save_as: "approval_result",
        },
        businessInputs: [
            "Decision"
        ],
        businessOutputs: [
            "Approved",
            "Rejected"
        ],

        runtimeNodeTypes: ["human.approval"],
    },
    {
        kind: "business_router",
        label: "Make Decision",
        description: "Chooses the next path based on customer intent, urgency, order status, or business rules.",
        category: "decision",
        icon: "split",
        ports: [
            { id: "in", label: "Input", kind: "input" },
            { id: "route_a", label: "Route A", kind: "output" },
            { id: "fallback", label: "Fallback", kind: "output" },
        ],
        defaultConfig: {
            key: "intent",
            rules: [{ when: "vars.intent == 'refund'", route: "refund" }],
            default_route: "fallback",
        },
        businessInputs: [
            "Intent",
            "Business rule"
        ],
        businessOutputs: [
            "Selected path",
            "Fallback path"
        ],

        runtimeNodeTypes: ["router.rules"],
    },
    {
        kind: "knowledge_answer",
        label: "Find Answer",
        description: "Finds the right policy, FAQ, or support article and prepares answer context.",
        category: "knowledge",
        icon: "book-open",
        ports: [
            { id: "in", label: "Question", kind: "input" },
            { id: "out", label: "Answer", kind: "output" },
        ],
        defaultConfig: {
            query_from: "last",
            top_k: 5,
            save_as: "knowledge_answer",
        },
        businessInputs: [
            "Customer question"
        ],
        businessOutputs: [
            "Knowledge answer"
        ],

        runtimeNodeTypes: ["kb.search", "llm.generate"],
    },
    {
        kind: "tool_action",
        label: "Tool Action",
        description: "Runs a connected action such as Shopify order lookup, shipping check, refund, or cancellation.",
        category: "action",
        icon: "package-search",
        ports: [
            { id: "in", label: "Input", kind: "input" },
            { id: "out", label: "Result", kind: "output" },
        ],
        defaultConfig: {
            name: "Tool Action",
            action: "shopify_get_order",
            order_ref_from: "last",
            order_ref_key: "order_ref",
            save_as: "tool_result",
        },
        businessInputs: [
            "Workflow input"
        ],
        businessOutputs: [
            "Tool result"
        ],
        runtimeNodeTypes: ["shopify.get_order", "shopify.order_action"],
    },

    {
        kind: "shopify_check_order",
        label: "Check Order",
        description: "Extract the order number from the customer message and retrieve Shopify order details.",
        category: "action",
        icon: "package-search",
        ports: [
            { id: "in", label: "Customer message", kind: "input" },
            { id: "out", label: "Order details", kind: "output" },
        ],
        defaultConfig: {
            name: "Check Order",
            save_as: "shopify_order",
            order_ref_key: "order_ref",
        },
        businessInputs: ["Customer message"],
        businessOutputs: ["Shopify order"],
        runtimeNodeTypes: ["customer_service.extract_order_ref", "shopify.get_order"],
    },
    {
        kind: "order_support_agent",
        label: "Order Support Agent",
        description: "Turn Shopify order data into a clear customer-facing support reply.",
        category: "agent",
        icon: "bot",
        ports: [
            { id: "in", label: "Order details", kind: "input" },
            { id: "out", label: "Customer reply", kind: "output" },
        ],
        defaultConfig: {
            name: "Order Support Agent",
            save_as: "reply",
            temperature: 0.2,
        },
        businessInputs: ["Shopify order"],
        businessOutputs: ["Customer reply"],
        runtimeNodeTypes: ["llm.generate"],
    },
    {
        kind: "customer_chat_reply",
        label: "Reply to Customer",
        description: "Send the final response back to the website chat widget and Inbox.",
        category: "response",
        icon: "send",
        ports: [{ id: "in", label: "Final response", kind: "input" }],
        defaultConfig: {
            message_from: "vars",
            message_key: "reply",
        },
        businessInputs: ["Final response"],
        businessOutputs: ["Reply sent"],
        runtimeNodeTypes: ["reply.customer_chat", "response"],
    },
    {
        kind: "send_response",
        label: "Reply to Customer",
        description: "Sends the final customer-facing reply after the workflow finishes.",
        category: "response",
        icon: "send",
        ports: [{ id: "in", label: "Answer", kind: "input" }],
        defaultConfig: {
            answer_from: "vars",
            answer_key: "agent_result",
            as_json: false,
        },
        businessInputs: [
            "Final response"
        ],
        businessOutputs: [
            "Reply sent"
        ],

        runtimeNodeTypes: ["response"],
    },
];

export function getBlockDefinition(kind: string) {
    return BLOCK_DEFINITIONS.find((block) => block.kind === kind);
}