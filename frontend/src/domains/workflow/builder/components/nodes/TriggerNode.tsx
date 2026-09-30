import { memo } from "react";
import { MessageCircle } from "lucide-react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

function TriggerNode({ id, data, selected }: NodeProps) {
    const d = data as any;
    const status = d.runStatus;

    return (
        <div className={`tajeran-node trigger ${selected ? "selected" : ""} ${status}`}>
            <Handle
                type="source"
                position={Position.Right}
                className="tajeran-handle tajeran-handle-source"
            />

            <div className="tajeran-node-badge">
                <MessageCircle size={14} />
            </div>

            <div className="tajeran-node-wrapper tajeran-gradient">
                <div className="tajeran-node-inner">
                    <div className="tajeran-node-body">
                        <div className="tajeran-node-icon">
                            <MessageCircle size={15} />
                        </div>

                        <div className="min-w-0 flex-1">
                            <div className="tajeran-node-title">Customer Message</div>
                            <div className="tajeran-node-subtitle">trigger.message</div>
                        </div>
                    </div>

                    <textarea
                        className="nodrag nowheel tajeran-node-textarea"
                        placeholder="User message..."
                        value={String(d.input ?? "")}
                        onChange={(e) => d.onChange?.(id, e.target.value)}
                    />

                    {status && (
                        <div className="tajeran-node-status">{status}</div>
                    )}

                </div>
            </div>
        </div>
    );
}

export default memo(TriggerNode);