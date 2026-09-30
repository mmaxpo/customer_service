import type { XYPosition } from "@xyflow/react";
import { getBlockDefinition } from "../blocks/blockDefinitions";
import type { ComposerBlockKind, ComposerNode } from "../types/composer";

export function createComposerBlock(
    kind: ComposerBlockKind,
    position: XYPosition,
    overrides: Record<string, any> = {}
): ComposerNode {
    const definition = getBlockDefinition(kind);

    if (!definition) {
        throw new Error(`Unknown composer block kind: ${kind}`);
    }

    const id = overrides.id ?? crypto.randomUUID();

    return {
        id,
        type: "composer",
        position,
        data: {
            blockKind: kind,
            label: overrides.label ?? definition.label,
            description: definition.description,
            category: definition.category,

            businessInputs: definition.businessInputs,
            businessOutputs: definition.businessOutputs,

            config: {
                ...definition.defaultConfig,
                ...overrides.config,
            },
            advanced: false,
        },
    };
}