import { apiFetch, apiJson, apiSseUrl, jsonBody } from "./client";

export type WorkflowRunResponse = {
    answer?: string;
    meta?: {
        status?: string;
        workflow_run_id?: string;
        interrupt?: any;
        final_state?: any;
    };
    workflow_run_id?: string;
    [key: string]: any;
};

export const workflowApi = {
    catalogNodes() {
        return apiJson("/api/workflows/catalog/nodes");
    },

    listSaved() {
        return apiJson("/api/workflows/runtime");
    },

    getSaved(workflowId: string) {
        return apiJson(`/api/workflows/runtime/${workflowId}`);
    },

    createSaved(payload: any) {
        return apiJson("/api/workflows/runtime", {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    updateSaved(workflowId: string, payload: any) {
        return apiJson(`/api/workflows/runtime/${workflowId}`, {
            method: "PUT",
            body: jsonBody(payload),
        });
    },

    run(payload: any) {
        return apiJson<WorkflowRunResponse>("/api/workflows/run", {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    runSaved(workflowId: string, payload: any) {
        return apiJson<WorkflowRunResponse>(`/api/workflows/runtime/${workflowId}/run`, {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    resume(payload: any) {
        return apiJson<WorkflowRunResponse>("/api/workflows/resume", {
            method: "POST",
            body: jsonBody(payload),
        });
    },

    listRuns(params = "limit=30&offset=0") {
        return apiJson(`/api/workflows/runs?${params}`);
    },

    runState(workflowRunId: string) {
        return apiJson(`/api/workflows/runs/${workflowRunId}/state`);
    },

    streamUrl(workflowRunId: string, afterSeq = 0) {
        return apiSseUrl(`/api/workflows/runs/${workflowRunId}/stream?after_seq=${afterSeq}`);
    },

    rawResume(payload: any) {
        return apiFetch("/api/workflows/resume", {
            method: "POST",
            body: jsonBody(payload),
        });
    },
    deleteSaved(workflowId: string) {
        return apiFetch(`/api/workflows/runtime/${workflowId}`, {
            method: "DELETE",
        });
    },
};
