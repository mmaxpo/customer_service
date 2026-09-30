import type { ComposerEdge, ComposerNode } from "../types/composer";

export function inferConnectionConfig(
    source: ComposerNode,
    target: ComposerNode
): Partial<ComposerEdge["data"]> {
    if (target.data.blockKind === "send_response") {
        return {
            autoConfigured: true,
            sourcePort: "out",
            targetPort: "in",
        };
    }

    if (source.data.blockKind === "business_router") {
        return {
            autoConfigured: true,
            route: "auto",
        };
    }

    return {
        autoConfigured: true,
    };
}

export function canConnectBlocks(source: ComposerNode, target: ComposerNode) {
    if (source.id === target.id) return false;
    if (target.data.category === "trigger") return false;
    if (source.data.category === "response") return false;
    return true;
}