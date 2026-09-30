import type { ComposerNode, RuntimeWorkflow } from "../types/composer";

function runtimeId(blockId: string, suffix: string) {
    return `${blockId}:${suffix}`;
}

export function buildRuntimeForBlock(block: ComposerNode): RuntimeWorkflow & { outputKey?: string } {
    const config = block.data.config;

    if (block.data.blockKind === "customer_message_trigger") {
        return {
            nodes: [
                {
                    id: runtimeId(block.id, "trigger"),
                    type: "trigger",
                    data: {
                        nodeType: "trigger.message",
                        input: config.input ?? "",
                    },
                },
            ],
            edges: [],
            outputKey: "input",
        };
    }

    if (block.data.blockKind === "ai_agent") {
        const saveAs = config.save_as || `${block.id.replaceAll("-", "_")}_result`;

        return {
            nodes: [
                {
                    id: runtimeId(block.id, "agent"),
                    type: "editable",
                    data: {
                        nodeType: "agent.custom",
                        name: config.name ?? "AI Agent",
                        save_as: saveAs,
                        backend: config.backend ?? "pure",
                        pattern: config.pattern ?? "tool_agent",
                        system_prompt: config.responsibility ?? config.system_prompt ?? "",
                        instruction: config.instruction ?? "",
                        input_from: "last",
                        input_key: "input",
                        tools: config.tools ?? [],
                        max_steps: config.max_steps ?? 5,
                    },
                },
            ],
            edges: [],
            outputKey: saveAs,
        };
    }

    if (block.data.blockKind === "parallel_agents") {
        const agents = Array.isArray(config.agents) ? config.agents : [];
        const joinId = runtimeId(block.id, "join");
        const outputKey = config.output_key || "parallel_result";

        const nodes: Array<Record<string, any>> = agents.map((agent: any, index: number) => ({
            id: runtimeId(block.id, `agent_${index + 1}`),
            type: "editable",
            data: {
                nodeType: "agent.custom",
                name: agent.name ?? `Agent ${index + 1}`,
                save_as: `${outputKey}_${index + 1}`,
                backend: "pure",
                pattern: "tool_agent",
                system_prompt: agent.responsibility ?? "",
                instruction: "",
                input_from: "last",
                input_key: "input",
                tools: agent.tools ?? [],
                max_steps: agent.max_steps ?? 5,
            },
        }));

        nodes.push({
            id: joinId,
            type: "editable",
            data: {
                nodeType: "join.all",
                name: "Join Results",
                save_as: outputKey,
            },
        });

        const edges = agents.map((_: any, index: number) => ({
            id: `${runtimeId(block.id, `agent_${index + 1}`)}-${joinId}`,
            source: runtimeId(block.id, `agent_${index + 1}`),
            target: joinId,
        }));

        return { nodes, edges, outputKey };
    }

    if (block.data.blockKind === "human_approval") {
        return {
            nodes: [
                {
                    id: runtimeId(block.id, "approval"),
                    type: "editable",
                    data: {
                        nodeType: "human.approval",
                        name: "Human Approval",
                        question: config.question ?? "Approve this action?",
                        save_as: config.save_as ?? "approval_result",
                    },
                },
            ],
            edges: [],
            outputKey: config.save_as ?? "approval_result",
        };
    }


    if (block.data.blockKind === "shopify_check_order") {
        const extractId = runtimeId(block.id, "extract_order_ref");
        const getOrderId = runtimeId(block.id, "shopify_get_order");
        const saveAs = config.save_as ?? "shopify_order";

        return {
            nodes: [
                {
                    id: extractId,
                    type: "editable",
                    data: {
                        nodeType: "customer_service.extract_order_ref",
                        name: "Extract Order Number",
                        input_from: "last",
                        save_as: config.order_ref_key ?? "order_ref",
                    },
                },
                {
                    id: getOrderId,
                    type: "editable",
                    data: {
                        nodeType: "shopify.get_order",
                        name: config.name ?? "Check Order",
                        order_ref_from: "vars",
                        order_ref_key: config.order_ref_key ?? "order_ref",
                        save_as: saveAs,
                    },
                },
            ],
            edges: [
                {
                    id: `${extractId}-${getOrderId}`,
                    source: extractId,
                    target: getOrderId,
                },
            ],
            outputKey: saveAs,
        };
    }

    if (block.data.blockKind === "order_support_agent") {
        const saveAs = config.save_as || "reply";

        return {
            nodes: [
                {
                    id: runtimeId(block.id, "llm_generate"),
                    type: "editable",
                    data: {
                        nodeType: "llm.generate",
                        name: config.name ?? "Order Support Agent",
                        system:
                            "You are Tajeran AI, a helpful Shopify support agent. Use the Shopify order context to answer clearly and briefly. Do not invent tracking or fulfillment data. If an order is unfulfilled, say it has not shipped yet.",
                        prompt:
                            "Customer message: {{input}}\n\nShopify order context: {{vars.shopify_order}}\n\nWrite a helpful customer-facing reply.",
                        temperature: config.temperature ?? 0.2,
                        save_as: saveAs,
                    },
                },
            ],
            edges: [],
            outputKey: saveAs,
        };
    }

    if (block.data.blockKind === "customer_chat_reply") {
        const replyId = runtimeId(block.id, "reply_customer_chat");
        const responseId = runtimeId(block.id, "response");

        return {
            nodes: [
                {
                    id: replyId,
                    type: "editable",
                    data: {
                        nodeType: "reply.customer_chat",
                        name: "Reply to Customer",
                        session_id_from: "extras",
                        session_id_key: "session_id",
                        message_from: config.message_from ?? "vars",
                        message_key: config.message_key ?? "reply",
                    },
                },
                {
                    id: responseId,
                    type: "editable",
                    data: {
                        nodeType: "response",
                        name: "Workflow Response",
                    },
                },
            ],
            edges: [
                {
                    id: `${replyId}-${responseId}`,
                    source: replyId,
                    target: responseId,
                },
            ],
            outputKey: undefined,
        };
    }

    if (block.data.blockKind === "tool_action") {
        const action = String(config.action || "");

        if (action === "shopify_get_order") {
            return {
                nodes: [
                    {
                        id: runtimeId(block.id, "shopify_get_order"),
                        type: "editable",
                        data: {
                            nodeType: "shopify.get_order",
                            name: config.name ?? "Check Order",
                            order_ref: config.order_ref ?? null,
                            order_ref_from: config.order_ref_from ?? "last",
                            order_ref_key: config.order_ref_key ?? "order_ref",
                            save_as: config.save_as ?? "shopify_order",
                        },
                    },
                ],
                edges: [],
                outputKey: config.save_as ?? "shopify_order",
            };
        }

        if (action === "shopify_shipping_status") {
            return {
                nodes: [
                    {
                        id: runtimeId(block.id, "shopify_shipping_status"),
                        type: "editable",
                        data: {
                            nodeType: "shopify.order_action",
                            name: config.name ?? "Check Shipping",
                            action: "shipping_status",
                            order_ref: config.order_ref ?? null,
                            order_ref_from: config.order_ref_from ?? "last",
                            order_ref_key: config.order_ref_key ?? "order_ref",
                            save_as: config.save_as ?? "shipping_status",
                        },
                    },
                ],
                edges: [],
                outputKey: config.save_as ?? "shipping_status",
            };
        }

        if (action === "shopify_refund_order") {
            return {
                nodes: [
                    {
                        id: runtimeId(block.id, "shopify_refund_order"),
                        type: "editable",
                        data: {
                            nodeType: "shopify.order_action",
                            name: config.name ?? "Refund Order",
                            action: "refund",
                            order_ref: config.order_ref ?? null,
                            order_ref_from: config.order_ref_from ?? "vars",
                            order_ref_key: config.order_ref_key ?? "order_ref",
                            reason: config.reason ?? "Customer service workflow refund",
                            amount: config.amount ?? null,
                            save_as: config.save_as ?? "refund_result",
                        },
                    },
                ],
                edges: [],
                outputKey: config.save_as ?? "refund_result",
            };
        }

        if (action === "shopify_cancel_order") {
            return {
                nodes: [
                    {
                        id: runtimeId(block.id, "shopify_cancel_order"),
                        type: "editable",
                        data: {
                            nodeType: "shopify.order_action",
                            name: config.name ?? "Cancel Order",
                            action: "cancel",
                            order_ref: config.order_ref ?? null,
                            order_ref_from: config.order_ref_from ?? "vars",
                            order_ref_key: config.order_ref_key ?? "order_ref",
                            reason: config.reason ?? "Customer service workflow cancellation",
                            save_as: config.save_as ?? "cancel_result",
                        },
                    },
                ],
                edges: [],
                outputKey: config.save_as ?? "cancel_result",
            };
        }

        return { nodes: [], edges: [] };
    }

    if (block.data.blockKind === "send_response") {
        return {
            nodes: [
                {
                    id: runtimeId(block.id, "response"),
                    type: "editable",
                    data: {
                        nodeType: "response",
                        name: "Final Response",
                        answer_from: config.answer_from ?? "vars",
                        answer_key: config.answer_key ?? "agent_result",
                        as_json: Boolean(config.as_json),
                    },
                },
            ],
            edges: [],
            outputKey: undefined,
        };
    }

    return { nodes: [], edges: [] };
}