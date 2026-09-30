"use client";

import React, { useCallback } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export type NodeKind =
| "trigger.message"
| "knowledge.search"
| "llm.chat"
| "respond"
| "router";

export type WFNodeData = {
    kind: NodeKind;
    name: string;
    config: Record<string, any>;
};

function kindLabel(kind: NodeKind) {
    switch (kind) {
        case "trigger.message":
            return "Trigger";
        case "knowledge.search":
            return "KB";
        case "llm.chat":
            return "LLM";
        case "respond":
            return "Respond";
        case "router":
            return "Router";
        default:
            return kind;
    }
}

export default function AgentNode(props: NodeProps) {
    const { id, data, selected } = props;
    const typed = data as WFNodeData;

    const onNameChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        // We don't update state from inside node (best practice).
        // The parent will provide an onNodeDataChange later.
        // For now: just keep it non-editable OR emit a custom event.
        // We'll handle it in Step 3 by passing a function in data.
        const fn = (typed as any).onChangeName as undefined | ((id: string, name: string) => void);
        fn?.(id, e.target.value);
    }, [id, typed]);

    return (
        <div
            style={{
                minWidth: 220,
                borderRadius: 12,
                border: selected ? "2px solid #111" : "1px solid #ddd",
                background: "#fff",
                boxShadow: selected ? "0 6px 18px rgba(0,0,0,0.12)" : "0 2px 10px rgba(0,0,0,0.06)",
                overflow: "hidden",
            }}
        >
            {/* target handle (incoming) */}
            <Handle type="target" position={Position.Left} />

            {/* header */}
            <div style={{ padding: 10, borderBottom: "1px solid #eee", display: "flex", gap: 8, alignItems: "center" }}>
        <span
            style={{
                fontSize: 12,
                padding: "2px 8px",
                borderRadius: 999,
                background: "#f3f4f6",
                border: "1px solid #e5e7eb",
            }}
        >
          {kindLabel(typed.kind)}
        </span>

                <input
                    className="nodrag"
                    value={typed.name}
                    onChange={onNameChange}
                    style={{
                        border: "1px solid #eee",
                        borderRadius: 8,
                        padding: "6px 8px",
                        width: "100%",
                        fontSize: 13,
                        outline: "none",
                    }}
                />
            </div>

            {/* body */}
            <div style={{ padding: 10, fontSize: 12, color: "#444" }}>
                <div style={{ marginBottom: 6, color: "#777" }}>id: {id}</div>
                <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {typed.kind === "knowledge.search" && <>k: {typed.config?.k ?? 5}</>}
                    {typed.kind === "llm.chat" && <>model: {typed.config?.model ?? "gpt-4o-mini"}</>}
                    {typed.kind === "respond" && <>template: {String(typed.config?.text ?? "").slice(0, 30)}…</>}
                </div>
            </div>

            {/* source handle (outgoing) */}
            <Handle type="source" position={Position.Right} />
        </div>
    );
}