import type { Connection } from "@xyflow/react";
import { addEdge } from "@xyflow/react";
import { canConnectBlocks, inferConnectionConfig } from "../blocks/blockConnectionRules";
import type { ComposerEdge, ComposerNode } from "../types/composer";

export function connectComposerBlocks(
    connection: Connection,
    nodes: ComposerNode[],
    edges: ComposerEdge[]
): ComposerEdge[] {
    const source = nodes.find((node) => node.id === connection.source);
    const target = nodes.find((node) => node.id === connection.target);

    if (!source || !target) return edges;
    if (!canConnectBlocks(source, target)) return edges;

    const data = inferConnectionConfig(source, target);

    return addEdge(
        {
            ...connection,
            id: `${connection.source}-${connection.target}`,
            data,
        },
        edges
    ) as ComposerEdge[];
}