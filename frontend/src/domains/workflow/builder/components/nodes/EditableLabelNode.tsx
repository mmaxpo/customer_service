"use client";

import { Bot, CheckCircle2, Circle, Clock3, XCircle } from "lucide-react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

type Data = {
    label?: string;
    nodeType?: string;
    runStatus?: "idle" | "running" | "done" | "failed" | "paused";
    onChange?: (id: string, label: string) => void;
    connectedAgentName?: string;
};

function statusIcon(status?: string) {
    if (status === "running") return <Clock3 size={13} />;
    if (status === "done") return <CheckCircle2 size={13} />;
    if (status === "failed") return <XCircle size={13} />;
    return <Circle size={13} />;
}

function statusLabel(status?: string) {
    return status || "idle";
}

export default function EditableLabelNode(props: NodeProps) {
    const { id, selected } = props;
    const data = props.data as Data;
    const status = data.runStatus;

    return (
        <div className={`tajeran-node ${selected ? "selected" : ""} ${status}`}>
            <Handle
                type="target"
                position={Position.Left}
                className="tajeran-handle tajeran-handle-target"
            />
            <Handle
                type="source"
                position={Position.Right}
                className="tajeran-handle tajeran-handle-source"
            />

            <div className="tajeran-node-badge">
                <Bot size={14} />
            </div>

            <div className="tajeran-node-wrapper tajeran-gradient">
                <div className="tajeran-node-inner">
                    <div className="tajeran-node-body">
                        <div className="tajeran-node-icon">
                            <Bot size={15} />
                        </div>

                        <div className="min-w-0 flex-1">
                            <input
                                className="nodrag tajeran-node-input"
                                value={data.label ?? ""}
                                onChange={(e) => data.onChange?.(id, e.target.value)}
                            />

                            <div className="tajeran-node-subtitle">
                                {data.nodeType === "tool.reference"
                                    ? data.connectedAgentName
                                        ? `Connected to ${data.connectedAgentName}`
                                        : "Connect this tool to an AI Agent"
                                    : data.nodeType ?? "workflow node"}
                            </div>
                        </div>
                    </div>

                    {status && (
                        <div className="tajeran-node-status">
                            {statusIcon(status)}
                            {statusLabel(status)}
                        </div>
                    )}


                </div>
            </div>
        </div>
    );
}