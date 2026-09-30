"use client";

import type { ComposerNode } from "../types/composer";

type Props = {
    selectedNode: ComposerNode | null;
    updateNodeConfig: (nodeId: string, patch: Record<string, any>) => void;
    updateNodeLabel: (nodeId: string, label: string) => void;
};

export default function BlockInspector({
                                           selectedNode,
                                           updateNodeConfig,
                                           updateNodeLabel,
                                       }: Props) {
    if (!selectedNode) {
        return (
            <aside className="w-96 border-l border-slate-200 bg-white p-4">
                <div className="font-semibold">Inspector</div>
                <p className="mt-2 text-sm text-slate-500">Select a block to edit it.</p>
            </aside>
        );
    }

    const data = selectedNode.data;
    const config = data.config || {};

    return (
        <aside className="w-96 border-l border-slate-200 bg-white p-4">
            <div className="font-semibold">Inspector</div>
            <div className="mt-1 text-xs text-slate-500">{data.blockKind}</div>

            <label className="mt-5 block text-sm font-medium">Name</label>
            <input
                className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={data.label}
                onChange={(e) => updateNodeLabel(selectedNode.id, e.target.value)}
            />

            {"responsibility" in config && (
                <>
                    <label className="mt-5 block text-sm font-medium">Responsibility</label>
                    <textarea
                        className="mt-2 min-h-28 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                        value={config.responsibility ?? ""}
                        onChange={(e) =>
                            updateNodeConfig(selectedNode.id, { responsibility: e.target.value })
                        }
                    />
                </>
            )}

            {"save_as" in config && (
                <>
                    <label className="mt-5 block text-sm font-medium">Output key</label>
                    <input
                        className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                        value={config.save_as ?? ""}
                        onChange={(e) => updateNodeConfig(selectedNode.id, { save_as: e.target.value })}
                    />
                </>
            )}

            {"tools" in config && (
                <>
                    <label className="mt-5 block text-sm font-medium">Tools JSON</label>
                    <textarea
                        className="mt-2 min-h-20 w-full rounded-xl border border-slate-200 px-3 py-2 font-mono text-xs"
                        value={JSON.stringify(config.tools ?? [], null, 2)}
                        onChange={(e) => {
                            try {
                                updateNodeConfig(selectedNode.id, { tools: JSON.parse(e.target.value) });
                            } catch {
                                // ignore invalid JSON while typing
                            }
                        }}
                    />
                </>
            )}

            {"input" in config && (
                <>
                    <label className="mt-5 block text-sm font-medium">Trigger message</label>
                    <textarea
                        className="mt-2 min-h-24 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                        value={config.input ?? ""}
                        onChange={(e) => updateNodeConfig(selectedNode.id, { input: e.target.value })}
                    />
                </>
            )}

            {"answer_key" in config && (
                <>
                    <label className="mt-5 block text-sm font-medium">Answer key</label>
                    <input
                        className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                        value={config.answer_key ?? ""}
                        onChange={(e) =>
                            updateNodeConfig(selectedNode.id, { answer_key: e.target.value })
                        }
                    />
                </>
            )}
        </aside>
    );
}