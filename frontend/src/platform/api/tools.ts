import { apiJson } from "./client";

export type AgentToolCatalogItem = {
    name: string;
    title: string;
    description: string;
    parameters: Record<string, any>;
    risk_level: "safe" | "sensitive" | "dangerous";
    requires_approval: boolean;
    provider: string;
};

export const toolsApi = {
    list() {
        return apiJson<{ tools: AgentToolCatalogItem[] }>("/api/catalog/tools");
    },
};