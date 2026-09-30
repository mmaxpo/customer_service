import type { Edge, Node } from "@xyflow/react";

export const initialNodes: Node[] = [
    {
        id: "t1",
        position: { x: 60, y: 60 },
        type: "trigger",
        data: { nodeType: "trigger.message", input: "what is our refund policy?" },
    },
    {
        id: "r1",
        position: { x: 520, y: 160 },
        type: "editable",
        data: { label: "✅ Response", nodeType: "response" },
    },
];

export const initialEdges: Edge[] = [
    { id: "e1", source: "t1", target: "r1" },
];