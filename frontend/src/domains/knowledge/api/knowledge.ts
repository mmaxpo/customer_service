import { apiJson, jsonBody } from "@/platform/api/client";

export const knowledgeApi = {
    docs() {
        return apiJson("/api/knowledge/docs");
    },

    ingest(payload: any) {
        return apiJson("/api/knowledge/ingest", {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    deleteDoc(docId: string) {
        return apiJson(`/api/knowledge/docs/${encodeURIComponent(docId)}`, {
            method: "DELETE",
        });
    },

    search(payload: any) {
        return apiJson("/api/knowledge/search", {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    askAgent(payload: any, debug = false) {
        return apiJson(`/api/knowledge/ask_agent?debug=${encodeURIComponent(String(debug))}`, {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    askAgentMcp(payload: any, debug = false) {
        return apiJson(`/api/knowledge/ask_agent_mcp?debug=${encodeURIComponent(String(debug))}`, {
            method: "POST",
            body: jsonBody(payload),
        });
    },
};
