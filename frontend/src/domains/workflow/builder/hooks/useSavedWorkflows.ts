import { useCallback, useEffect, useState } from "react";
import type { Edge, Node } from "@xyflow/react";
import { ApiError, workflowApi } from "@/platform/api";
import { normalizeWorkflowNodes } from "@/domains/workflow/builder/utils/normalizeWorkflowNodes";

type SavedWorkflow = {
    id: string;
    name: string;
};


export function useSavedWorkflows(
    nodes: Node[],
    edges: Edge[],
    setNodes: (nodes: Node[]) => void,
    setEdges: (edges: Edge[]) => void
) {
    const [saved, setSaved] = useState<SavedWorkflow[]>([]);
    const [savedStatus, setSavedStatus] = useState("");
    const [selectedWorkflowId, setSelectedWorkflowId] = useState("");
    const [saveName, setSaveName] = useState("My Workflow");

    const refreshSaved = useCallback(async () => {
        setSavedStatus("Loading saved workflows...");

        try {
            const data = await workflowApi.listSaved();
            const items = (data.items ?? []).map((x: any) => ({
                id: String(x.id),
                name: String(x.name),
            }));

            setSaved(items);
            setSavedStatus(`OK (${items.length})`);
        } catch (e: any) {
            setSavedStatus(`Error: ${String(e?.message ?? e)}`);
        }
    }, []);

    useEffect(() => {
        refreshSaved();
    }, [refreshSaved]);

    const loadSaved = useCallback(async () => {
        if (!selectedWorkflowId) return;

        setSavedStatus("Loading workflow...");

        let data: any;

        try {
            data = await workflowApi.getSaved(selectedWorkflowId);
        } catch (e: any) {
            if (e instanceof ApiError) {
                setSavedStatus(`Load failed: ${e.status} ${e.body || ""}`);
                return;
            }

            setSavedStatus(`Load error: ${String(e?.message ?? e)}`);
            return;
        }

        const wf = data.workflow ?? {};

        setNodes(normalizeWorkflowNodes(wf.nodes ?? []));
        setEdges(wf.edges ?? []);
        setSaveName(String(data.name ?? ""));
        setSelectedWorkflowId(String(data.id ?? selectedWorkflowId));
        setSavedStatus("Loaded");
    }, [selectedWorkflowId, setNodes, setEdges]);

    const saveWorkflow = useCallback(async () => {
        setSavedStatus("Saving...");

        const name =
            (saveName || "").trim() ||
            `Workflow ${new Date().toISOString().slice(0, 16).replace("T", " ")}`;

        const normalizedNodes = normalizeWorkflowNodes(nodes);

        const payload = {
            name,
            workflow: {
                nodes: normalizedNodes,
                edges,
            },
        };

        try {
            if (selectedWorkflowId) {
                await workflowApi.updateSaved(selectedWorkflowId, payload);
                setSavedStatus(`Updated: ${name}`);
            } else {
                const data: any = await workflowApi.createSaved(payload);
                setSelectedWorkflowId(String(data.id));
                setSavedStatus(`Created: ${data.name}`);
            }
        } catch (e: any) {
            if (e instanceof ApiError) {
                setSavedStatus(`Save failed: ${e.status} ${e.body || ""}`);
                return;
            }

            setSavedStatus(`Save error: ${String(e?.message ?? e)}`);
            return;
        }

        setNodes(normalizedNodes);
        await refreshSaved();
        setSaveName(name);
    }, [nodes, edges, saveName, selectedWorkflowId, refreshSaved, setNodes]);
    const renameWorkflow = useCallback(
        async (id: string, name: string) => {
            const nextName = name.trim();
            if (!id || !nextName) return;

            setSavedStatus("Renaming...");

            try {
                const current = await workflowApi.getSaved(id);
                await workflowApi.updateSaved(id, {
                    name: nextName,
                    workflow: current.workflow ?? { nodes: [], edges: [] },
                });

                if (selectedWorkflowId === id) {
                    setSaveName(nextName);
                }

                await refreshSaved();
                setSavedStatus(`Renamed: ${nextName}`);
            } catch (e: any) {
                if (e instanceof ApiError) {
                    setSavedStatus(`Rename failed: ${e.status} ${e.body || ""}`);
                    return;
                }

                setSavedStatus(`Rename error: ${String(e?.message ?? e)}`);
            }
        },
        [selectedWorkflowId, refreshSaved]
    );

    const deleteWorkflow = useCallback(
        async (id: string) => {
            if (!id) return;

            const ok = window.confirm("Delete this saved workflow?");
            if (!ok) return;

            setSavedStatus("Deleting...");

            try {
                await workflowApi.deleteSaved(id);

                if (selectedWorkflowId === id) {
                    setSelectedWorkflowId("");
                    setSaveName("My Workflow");
                }

                await refreshSaved();
                setSavedStatus("Deleted");
            } catch (e: any) {
                if (e instanceof ApiError) {
                    setSavedStatus(`Delete failed: ${e.status} ${e.body || ""}`);
                    return;
                }

                setSavedStatus(`Delete error: ${String(e?.message ?? e)}`);
            }
        },
        [selectedWorkflowId, refreshSaved]
    );
    return {
        saved,
        savedStatus,
        selectedWorkflowId,
        saveName,
        setSelectedWorkflowId,
        setSaveName,
        setSavedStatus,
        refreshSaved,
        loadSaved,
        saveWorkflow,
        renameWorkflow,
        deleteWorkflow,
    };
}