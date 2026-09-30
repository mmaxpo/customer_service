import { useCallback, useMemo, useState } from "react";
import type { Edge, Node, OnSelectionChangeParams } from "@xyflow/react";

export function useWorkflowSelection(
    nodes: Node[],
    setNodes: React.Dispatch<React.SetStateAction<Node[]>>,
    setEdges: React.Dispatch<React.SetStateAction<Edge[]>>
) {
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [selectedEdgeIds, setSelectedEdgeIds] = useState<string[]>([]);

    const selectedNode = useMemo(
        () => nodes.find((n) => n.id === selectedNodeId) ?? null,
        [nodes, selectedNodeId]
    );

    const onSelectionChange = useCallback((p: OnSelectionChangeParams) => {
        setSelectedNodeId((p.nodes || [])[0]?.id ?? null);
        setSelectedEdgeIds((p.edges || []).map((e) => e.id));
    }, []);

    const deleteSelected = useCallback(() => {
        if (!selectedNodeId && selectedEdgeIds.length === 0) return;

        setNodes((nds) =>
            selectedNodeId ? nds.filter((n) => n.id !== selectedNodeId) : nds
        );

        setEdges((eds) => {
            let out = eds.filter((e) => !selectedEdgeIds.includes(e.id));

            if (selectedNodeId) {
                out = out.filter(
                    (e) => e.source !== selectedNodeId && e.target !== selectedNodeId
                );
            }

            return out;
        });

        setSelectedNodeId(null);
        setSelectedEdgeIds([]);
    }, [selectedNodeId, selectedEdgeIds, setNodes, setEdges]);

    return {
        selectedNode,
        selectedNodeId,
        selectedEdgeIds,
        onSelectionChange,
        deleteSelected,
    };
}