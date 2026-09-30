import {useCallback, useMemo} from "react";
import type {Node} from "@xyflow/react";
import type {CatalogItem} from "@/domains/workflow/builder/types/catalog";
import {
    buildDefaultConfig,
    safeNodeLabel,
} from "@/domains/workflow/builder/utils/catalog";

export function useWorkflowNodes(
    nodes: Node[],
    setNodes: React.Dispatch<React.SetStateAction<Node[]>>,
    selectedNodeId: string | null,
    nodeStatus: Record<string, any> = {}
) {
    const nodesWithHandlers = useMemo(() => {

        return nodes.map((n) => ({
            ...n,
            data: {
                ...n.data,
                runStatus: nodeStatus[n.id],
                onChange: (id: string, value: string) => {
                    setNodes((nds) =>
                        nds.map((x) => {
                            if (x.id !== id) return x;
                            if (x.type === "trigger") {
                                return {...x, data: {...x.data, input: value}};
                            }
                            return {...x, data: {...x.data, label: value}};
                        })
                    );
                },
            },

        }));
    }, [nodes, setNodes, nodeStatus]);

    const addNode = useCallback(
        (item: CatalogItem) => {
            const id = crypto.randomUUID();
            const base = buildDefaultConfig(item);

            if (item.node_type === "trigger.message") {
                setNodes((nds) => [
                    ...nds,
                    {
                        id,
                        type: "trigger",
                        position: {x: 100 + nds.length * 40, y: 80 + nds.length * 30},
                        data: base,
                    },
                ]);
                return;
            }

            setNodes((nds) => [
                ...nds,
                {
                    id,
                    type: "editable",
                    position: {x: 100 + nds.length * 40, y: 80 + nds.length * 30},
                    data: {label: safeNodeLabel(item), ...base},
                },
            ]);
        },
        [setNodes]
    );

    const updateSelectedNodeField = useCallback(
        (key: string, value: any) => {
            if (!selectedNodeId) return;

            setNodes((nds) =>
                nds.map((n) => {
                    if (n.id !== selectedNodeId) return n;
                    return {...n, data: {...(n.data as any), [key]: value}};
                })
            );
        },
        [selectedNodeId, setNodes]
    );

    return {
        nodesWithHandlers,
        addNode,
        updateSelectedNodeField,
    };
}