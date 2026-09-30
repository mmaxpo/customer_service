import { useCallback, useState } from "react";
import type { Edge, Node } from "@xyflow/react";

export function useWorkflowImportExport(
    nodes: Node[],
    edges: Edge[],
    setNodes: (nodes: Node[]) => void,
    setEdges: (edges: Edge[]) => void,
    setSavedStatus: (value: string) => void
) {
    const [importText, setImportText] = useState("");
    const [showImport, setShowImport] = useState(false);

    const importWorkflow = useCallback(() => {
        try {
            const parsed = JSON.parse(importText);

            if (!parsed?.nodes || !parsed?.edges) {
                alert("Invalid workflow format");
                return;
            }

            setNodes(parsed.nodes);
            setEdges(parsed.edges);
            setShowImport(false);
            setSavedStatus("Imported (not saved yet)");
        } catch {
            alert("Invalid JSON");
        }
    }, [importText, setNodes, setEdges, setSavedStatus]);

    const exportWorkflow = useCallback(() => {
        const data = { nodes, edges };
        navigator.clipboard.writeText(JSON.stringify(data, null, 2));
        setSavedStatus("Exported to clipboard");
    }, [nodes, edges, setSavedStatus]);

    return {
        importText,
        setImportText,
        showImport,
        setShowImport,
        importWorkflow,
        exportWorkflow,
    };
}