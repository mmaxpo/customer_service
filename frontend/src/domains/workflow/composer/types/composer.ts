import type { Edge, Node } from "@xyflow/react";

export type ComposerBlockCategory =
    | "trigger"
    | "agent"
    | "decision"
    | "approval"
    | "action"
    | "knowledge"
    | "join"
    | "response"
    | "group";

export type ComposerRuntimeNodeType =
    | "trigger.message"
    | "agent.custom"
    | "router.rules"
    | "router.llm"
    | "human.approval"
    | "set.variable"
    | "join.all"
    | "response"
    | "kb.search"
    | "llm.generate"
    | "web.search"
    | "web.fetch_extract"
    | "customer_service.extract_order_ref"
    | "shopify.get_order"
    | "shopify.order_action"
    | "reply.customer_chat";

export type ComposerBlockKind =
    | "customer_message_trigger"
    | "ai_agent"
    | "parallel_agents"
    | "human_approval"
    | "business_router"
    | "knowledge_answer"
    | "tool_action"
    | "shopify_check_order"
    | "order_support_agent"
    | "customer_chat_reply"
    | "join_results"
    | "send_response";

export type ComposerPort = {
    id: string;
    label: string;
    kind: "input" | "output";
};

export type ComposerBlockDefinition = {
    kind: ComposerBlockKind;
    label: string;
    description: string;
    category: ComposerBlockCategory;
    icon: string;
    ports: ComposerPort[];

    businessInputs: string[];
    businessOutputs: string[];

    defaultConfig: Record<string, any>;
    runtimeNodeTypes: ComposerRuntimeNodeType[];
};

export type ComposerBlockInstanceData = {
    blockKind: ComposerBlockKind;
    label: string;
    description?: string;
    category: ComposerBlockCategory;

    businessInputs?: string[];
    businessOutputs?: string[];

    config: Record<string, any>;
    runtime?: {
        nodes: Array<Record<string, any>>;
        edges: Array<Record<string, any>>;
        outputKey?: string;
    };
    advanced?: boolean;
};

export type ComposerNode = Node<ComposerBlockInstanceData>;
export type ComposerEdge = Edge<{
    sourcePort?: string;
    targetPort?: string;
    route?: string;
    autoConfigured?: boolean;
}>;

export type RuntimeWorkflow = {
    nodes: Array<Record<string, any>>;
    edges: Array<Record<string, any>>;
};