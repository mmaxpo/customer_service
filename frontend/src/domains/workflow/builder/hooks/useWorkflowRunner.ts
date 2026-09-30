import { useCallback, useState } from "react";
import type { Edge, Node } from "@xyflow/react";
import { ApiError, workflowApi, type WorkflowRunResponse } from "@/platform/api";
import { useRunStore } from "@/domains/workflow/runner/store/runStore";
import { buildRuntimePayload } from "@/domains/workflow/builder/utils/runtimePayload";

type PendingApproval = {
    workflowRunId: string;
    question: string;
    interrupt: any;
} | null;

function getWorkflowRunId(data: any) {
    return String(data?.meta?.workflow_run_id ?? data?.workflow_run_id ?? "");
}

export function useWorkflowRunner(nodes: Node[], edges: Edge[], selectedWorkflowId: string) {
    const [workflowRunId, setWorkflowRunId] = useState("");
    const [runStatus, setRunStatus] = useState("");
    const [runAnswer, setRunAnswer] = useState("");
    const setStoreRunId = useRunStore((s) => s.setRunId);
    const [pendingApproval, setPendingApproval] = useState<PendingApproval>(null);

    const handleRunResponse = useCallback(
        (data: WorkflowRunResponse) => {
            const nextWorkflowRunId = getWorkflowRunId(data);

            if (nextWorkflowRunId) {
                setWorkflowRunId(nextWorkflowRunId);
                setStoreRunId(nextWorkflowRunId);
            }

            if (data.meta?.status === "paused") {
                setRunStatus(
                    `Paused: waiting for approval${
                        nextWorkflowRunId ? ` • ${nextWorkflowRunId.slice(0, 8)}` : ""
                    }`
                );
                setPendingApproval({
                    workflowRunId: nextWorkflowRunId,
                    question: String(data.meta.interrupt?.question ?? "Approve?"),
                    interrupt: data.meta.interrupt,
                });
                return;
            }

            setRunAnswer(String(data.answer ?? ""));
            setRunStatus(
                `OK: ${data.meta?.status ?? "unknown"}${
                    nextWorkflowRunId ? ` • ${nextWorkflowRunId.slice(0, 8)}` : ""
                }`
            );
            setPendingApproval(null);
        },
        [setStoreRunId]
    );

    const runWorkflow = useCallback(async () => {
        setWorkflowRunId("");
        setRunStatus("Running...");
        setRunAnswer("");
        setPendingApproval(null);

        try {
            const payload = buildRuntimePayload(nodes, edges);

            const data = await workflowApi.run({
                ...payload,
                thread_id: crypto.randomUUID(),
            });

            handleRunResponse(data);
        } catch (e: any) {
            if (e instanceof ApiError) setRunStatus(`Run failed: ${e.status} ${e.body}`);
            else setRunStatus(`Run error: ${String(e?.message ?? e)}`);
        }
    }, [nodes, edges, handleRunResponse]);

    const runSavedWorkflow = useCallback(async () => {
        if (!selectedWorkflowId) return;

        setWorkflowRunId("");
        setRunStatus("Running saved...");
        setRunAnswer("");
        setPendingApproval(null);

        try {
            const payload = buildRuntimePayload(nodes, edges);

            const data = await workflowApi.run({
                ...payload,
                thread_id: crypto.randomUUID(),
            });

            handleRunResponse(data);
        } catch (e: any) {
            if (e instanceof ApiError) setRunStatus(`Run saved failed: ${e.status} ${e.body}`);
            else setRunStatus(`Run saved error: ${String(e?.message ?? e)}`);
        }
    }, [selectedWorkflowId, nodes, edges, handleRunResponse]);

    const resumeApproval = useCallback(
        async (approved: boolean) => {
            if (!pendingApproval) return;

            const currentWorkflowRunId = pendingApproval.workflowRunId;

            setPendingApproval(null);
            setRunStatus(approved ? "Approving..." : "Rejecting...");

            try {
                const data = await workflowApi.resume({
                    workflow_run_id: currentWorkflowRunId,
                    input: { approved },
                    strict: true,
                });

                handleRunResponse(data);
            } catch (e: any) {
                if (e instanceof ApiError) setRunStatus(`Resume failed: ${e.status} ${e.body}`);
                else setRunStatus(`Resume error: ${String(e?.message ?? e)}`);
            }
        },
        [pendingApproval, handleRunResponse]
    );

    return {
        workflowRunId,
        runStatus,
        runAnswer,
        setRunAnswer,
        runWorkflow,
        runSavedWorkflow,
        pendingApproval,
        resumeApproval,
    };
}