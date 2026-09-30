"use client";

import { useMemo } from "react";
import { useRunStore } from "../../../runner/store/runStore";

type Props = {
    runAnswer: string;
    setRunAnswer: (value: string) => void;
    runStatus: string;
};

function badgeColor(value?: string) {
    if (value === "run_end" || value === "node_end" || value === "done") return "#16a34a";
    if (value === "run_start" || value === "node_start" || value === "running") return "#2563eb";
    if (value === "run_paused" || value === "paused") return "#d97706";
    if (value === "run_failed" || value === "node_error" || value === "failed") return "#dc2626";
    return "#64748b";
}

function shortId(id?: string | null) {
    if (!id) return "";
    return id.length > 12 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
}

export default function RunOutputPanel({
                                           runAnswer,
                                           setRunAnswer,
                                           runStatus,
                                       }: Props) {
    const events = useRunStore((s) => s.events);
    const workflowRunId = useRunStore((s) => s.runId);
    const status = useRunStore((s) => s.status);
    const pauseInterrupt = useRunStore((s) => s.pauseInterrupt);

    const renderedEvents = useMemo(() => [...events].reverse(), [events]);

    const agentEvents = useMemo(() => {
        return events.filter((item) => {
            const ev = item.event || {};
            const meta = ev.meta || {};
            return Boolean(
                ev.agent_run_id ||
                ev.agent_status ||
                ev.agent_steps ||
                ev.agent_pending_approval ||
                meta.agent_run_id ||
                meta.agent_status ||
                meta.agent_steps ||
                meta.agent_pending_approval
            );
        });
    }, [events]);

    return (
        <div style={{ padding: 12 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ fontWeight: 700 }}>Run Output</div>
                <button onClick={() => setRunAnswer("")} disabled={!runAnswer}>
                    Clear
                </button>
            </div>

            <div style={{ marginTop: 10, padding: 10, border: "1px solid #eee", borderRadius: 10 }}>
                <div style={{ fontSize: 12, color: "#666" }}>Workflow Run</div>

                <div style={{ marginTop: 6, fontSize: 13 }}>
                    <strong>Status:</strong>{" "}
                    <span style={{ color: badgeColor(status), fontWeight: 700 }}>
                        {status || runStatus || "idle"}
                    </span>
                </div>

                <div style={{ marginTop: 4, fontSize: 12, color: "#555" }}>
                    <strong>ID:</strong> {workflowRunId ? shortId(workflowRunId) : "No run yet"}
                </div>

                {pauseInterrupt && (
                    <div style={{ marginTop: 8, color: "#d97706", fontSize: 12 }}>
                        Waiting for approval
                    </div>
                )}
            </div>

            <div style={{ marginTop: 12, padding: 12, border: "1px solid #eee", borderRadius: 10 }}>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Final Answer</div>
                <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>
                    {runAnswer || "No answer yet"}
                </div>
            </div>

            <div style={{ marginTop: 16, padding: 12, border: "1px solid #eee", borderRadius: 10 }}>
                <div style={{ fontWeight: 700, marginBottom: 10 }}>Agent Trace</div>

                {agentEvents.length === 0 ? (
                    <div style={{ color: "#777", fontSize: 13 }}>No agent trace yet</div>
                ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {agentEvents.map((item) => {
                            const ev = item.event || {};
                            const meta = ev.meta || {};
                            const agentRunId = ev.agent_run_id || meta.agent_run_id;
                            const agentStatus = ev.agent_status || meta.agent_status;
                            const agentSteps = ev.agent_steps ?? meta.agent_steps;

                            return (
                                <div
                                    key={`agent-${item.seq}`}
                                    style={{
                                        border: "1px solid #f0f0f0",
                                        borderRadius: 8,
                                        padding: 10,
                                        fontSize: 12,
                                        background: "#fafafa",
                                    }}
                                >
                                    <div style={{ fontWeight: 700 }}>
                                        {ev.node_id || "agent node"}
                                    </div>

                                    {agentRunId && (
                                        <div>agent_run_id: {shortId(agentRunId)}</div>
                                    )}

                                    {agentStatus && (
                                        <div>
                                            status:{" "}
                                            <span style={{ color: badgeColor(agentStatus), fontWeight: 700 }}>
                        {agentStatus}
                    </span>
                                        </div>
                                    )}

                                    {typeof agentSteps !== "undefined" && (
                                        <div>steps: {agentSteps}</div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            <div
                style={{
                    marginTop: 16,
                    padding: 12,
                    border: "1px solid #eee",
                    borderRadius: 10,
                    maxHeight: 420,
                    overflow: "auto",
                }}
            >
                <div style={{ fontWeight: 700, marginBottom: 10 }}>Live Events</div>

                {renderedEvents.length === 0 && (
                    <div style={{ color: "#777", fontSize: 13 }}>No events yet</div>
                )}

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {renderedEvents.map((item) => {
                        const ev = item.event || {};
                        const type = ev.event || "unknown";

                        return (
                            <div
                                key={item.seq}
                                style={{
                                    border: "1px solid #f0f0f0",
                                    borderRadius: 8,
                                    padding: 10,
                                    fontSize: 12,
                                    background: "#fafafa",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                                    <span style={{ color: badgeColor(type), fontWeight: 700 }}>
                                        {type}
                                    </span>
                                    <span style={{ color: "#777" }}>seq {item.seq}</span>
                                </div>

                                {ev.node_id && <div style={{ marginTop: 4 }}>node: {ev.node_id}</div>}
                                {ev.node_type && <div>type: {ev.node_type}</div>}
                                {ev.agent_run_id && <div>agent: {shortId(ev.agent_run_id)}</div>}

                                {item.created_at && (
                                    <div style={{ marginTop: 4, color: "#777" }}>
                                        {new Date(item.created_at).toLocaleTimeString()}
                                    </div>
                                )}

                                {ev.error && (
                                    <div style={{ color: "crimson", marginTop: 6, whiteSpace: "pre-wrap" }}>
                                        {ev.error}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}