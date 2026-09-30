import { buildRuntimeForBlock } from "../blocks/blockFactory";
import type { ComposerEdge, ComposerNode, RuntimeWorkflow } from "../types/composer";

export function compileToRuntimeWorkflow(
    nodes: ComposerNode[],
    edges: ComposerEdge[]
): RuntimeWorkflow {
    const runtimeByBlockId = new Map<string, ReturnType<typeof buildRuntimeForBlock>>();

    for (const node of nodes) {
        runtimeByBlockId.set(node.id, buildRuntimeForBlock(node));
    }

    const runtimeNodes = Array.from(runtimeByBlockId.values()).flatMap((item) => item.nodes);
    const runtimeEdges = Array.from(runtimeByBlockId.values()).flatMap((item) => item.edges);

    for (const edge of edges) {
        const sourceRuntime = runtimeByBlockId.get(edge.source);
        const targetRuntime = runtimeByBlockId.get(edge.target);

        if (!sourceRuntime || !targetRuntime) continue;

        const sourceLast = sourceRuntime.nodes[sourceRuntime.nodes.length - 1];
        const targetFirst = targetRuntime.nodes[0];

        if (!sourceLast || !targetFirst) continue;

        runtimeEdges.push({
            id: `${sourceLast.id}-${targetFirst.id}`,
            source: sourceLast.id,
            target: targetFirst.id,
            data: edge.data,
        });

        const targetBlock = nodes.find((node) => node.id === edge.target);

        if (targetBlock?.data.blockKind === "send_response" && sourceRuntime.outputKey) {
            targetFirst.data.answer_from = "vars";
            targetFirst.data.answer_key = sourceRuntime.outputKey;
        }
    }

    return {
        nodes: runtimeNodes,
        edges: runtimeEdges,
    };
}