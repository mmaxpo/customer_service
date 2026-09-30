"use client";

import { useMemo, useState } from "react";
import { useRunStore } from "../store/runStore";
import { workflowApi } from "@/platform/api";
import PauseModal from "./PauseModal";
import { ReactFlow, Background, Controls } from "@xyflow/react";
import { useRunHydration } from "../hooks/useRunHydration";
import { useRunStream } from "../hooks/useRunStream";

export default function RunnerShell({ runId }: { runId: string }) {
    useRunHydration(runId);
    useRunStream(runId);
    const state = useRunStore((s) => s.state);
    const status = useRunStore((s) => s.status);
    const workflow = useRunStore((s) => s.workflow);
    const nodeStatus = useRunStore((s) => s.nodeStatus);
    const events = useRunStore((s) => s.events);
    const pauseInterrupt = useRunStore((s) => s.pauseInterrupt);

    const [resumeStatus, setResumeStatus] = useState("");
    const [approvalReason, setApprovalReason] = useState("");
    const vars = state?.vars ?? {};
    const nodeMetaById = state?.meta?.node_meta_by_id ?? {};

    const agentTraces = Object.entries(nodeMetaById)
        .filter(([_, meta]: any) => meta?.agent_run_id)
        .map(([nodeId, meta]: any) => ({
            nodeId,
            agentRunId: meta.agent_run_id,
            status: meta.agent_status,
            steps: meta.agent_steps,
            errors: meta.agent_errors ?? [],
        }));
    const { nodes, edges } = useMemo(() => {
        const wf = workflow || { nodes: [], edges: [] };

        const nodes = (wf.nodes || []).map((n: any) => {
            const st = nodeStatus[n.id] ?? "idle";
            const base = n.data?.nodeType ?? "node";
            return {
                id: n.id,
                position: n.position || { x: 0, y: 0 },
                type: "default",
                data: { label: `${base} • ${st}` },
            };
        });

        const edges = (wf.edges || []).map((e: any) => ({
            id: e.id,
            source: e.source,
            target: e.target,
        }));

        return { nodes, edges };
    }, [workflow, nodeStatus]);

    async function resume(approved: boolean) {
        setResumeStatus(approved ? "Approving..." : "Rejecting...");

        const res = await workflowApi.rawResume({
            workflow_run_id: runId,
            input: {
                approved,
                reason: approvalReason || undefined,
            },
            strict: true,
        });

        if (!res.ok) {
            const txt = await res.text();
            setResumeStatus(`Resume failed: ${res.status} ${txt}`);
            return;
        }

        setApprovalReason("");
        setResumeStatus(approved ? "Approved. Streaming will continue." : "Rejected. Streaming will continue.");
    }

    const paused = status === "paused";

    const interruptText =
        pauseInterrupt
            ? JSON.stringify(pauseInterrupt, null, 2).slice(0, 2000)
            : "";

    return (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", height: "calc(100vh - 64px)" }}>
            <div style={{ borderRight: "1px solid #eee" }}>
                <ReactFlow nodes={nodes} edges={edges} fitView>
                    <Background />
                    <Controls />
                </ReactFlow>
            </div>

            <div style={{ padding: 14, overflow: "auto" }}>
                <div style={{ fontSize: 12, color: "#666" }}>workflow_run_id</div>
                <div style={{ fontFamily: "monospace", fontSize: 12 }}>{runId}</div>

                <div style={{ marginTop: 10 }}>
                    <b>Status:</b> {status}
                </div>

                {resumeStatus && <div style={{ marginTop: 8, color: "#555" }}>{resumeStatus}</div>}
                {paused && (
                    <div
                        style={{
                            marginTop: 14,
                            border: "1px solid #f59e0b",
                            background: "#fffbeb",
                            borderRadius: 12,
                            padding: 12,
                        }}
                    >
                        <div style={{ fontWeight: 800, color: "#92400e" }}>
                            Human approval required
                        </div>

                        {pauseInterrupt?.question && (
                            <div style={{ marginTop: 8, fontSize: 13 }}>
                                {pauseInterrupt.question}
                            </div>
                        )}

                        {pauseInterrupt?.tool_name && (
                            <div style={{ marginTop: 8, fontSize: 12 }}>
                                <b>Tool:</b> {pauseInterrupt.tool_name}
                            </div>
                        )}

                        {pauseInterrupt?.arguments && (
                            <pre
                                style={{
                                    marginTop: 8,
                                    whiteSpace: "pre-wrap",
                                    fontSize: 12,
                                    background: "white",
                                    border: "1px solid #fde68a",
                                    borderRadius: 8,
                                    padding: 8,
                                }}
                            >
                {JSON.stringify(pauseInterrupt.arguments, null, 2)}
            </pre>
                        )}

                        <textarea
                            value={approvalReason}
                            onChange={(e) => setApprovalReason(e.target.value)}
                            placeholder="Optional reason / note..."
                            style={{
                                marginTop: 10,
                                width: "100%",
                                minHeight: 70,
                                borderRadius: 8,
                                border: "1px solid #fcd34d",
                                padding: 8,
                                fontSize: 13,
                            }}
                        />

                        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                            <button
                                onClick={() => resume(false)}
                                style={{
                                    padding: "8px 12px",
                                    borderRadius: 10,
                                    border: "1px solid #dc2626",
                                    color: "#dc2626",
                                    background: "white",
                                    cursor: "pointer",
                                }}
                            >
                                Reject
                            </button>

                            <button
                                onClick={() => resume(true)}
                                style={{
                                    padding: "8px 12px",
                                    borderRadius: 10,
                                    border: "1px solid #16a34a",
                                    background: "#16a34a",
                                    color: "white",
                                    cursor: "pointer",
                                }}
                            >
                                Approve
                            </button>
                        </div>
                    </div>
                )}
                <div style={{ marginTop: 14, borderTop: "1px solid #eee", paddingTop: 12 }}>
                    <b>State Vars</b>
                    <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>
        {JSON.stringify(vars, null, 2)}
    </pre>
                </div>

                <div style={{ marginTop: 14, borderTop: "1px solid #eee", paddingTop: 12 }}>
                    <b>Agent Trace</b>

                    {agentTraces.length === 0 ? (
                        <div style={{ fontSize: 12, color: "#777", marginTop: 8 }}>
                            No agent trace
                        </div>
                    ) : (
                        agentTraces.map((a) => (
                            <div
                                key={a.nodeId}
                                style={{
                                    border: "1px solid #eee",
                                    borderRadius: 10,
                                    padding: 10,
                                    marginTop: 10,
                                    fontSize: 12,
                                }}
                            >
                                <div><b>node:</b> {a.nodeId}</div>
                                <div><b>agent_run_id:</b> {a.agentRunId}</div>
                                <div><b>status:</b> {a.status}</div>
                                <div><b>steps:</b> {a.steps}</div>

                                {a.errors.length > 0 && (
                                    <pre style={{ color: "crimson", whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(a.errors, null, 2)}
                    </pre>
                                )}
                            </div>
                        ))
                    )}
                </div>
                <div style={{ marginTop: 14, borderTop: "1px solid #eee", paddingTop: 12 }}>
                    <b>Events</b>
                    <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
                        Showing last {Math.min(events.length, 200)} events
                    </div>

                    <div style={{ marginTop: 10 }}>
                        {events.slice(-200).map((e) => (
                            <div key={e.seq} style={{ border: "1px solid #f0f0f0", borderRadius: 10, padding: 10, marginBottom: 10 }}>
                                <div style={{ fontSize: 12, color: "#666" }}>
                                    seq: <b>{e.seq}</b> • {e.event?.event ?? "event"}
                                </div>
                                <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, margin: "8px 0 0 0" }}>
                  {JSON.stringify(e.event, null, 2)}
                </pre>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <PauseModal
                open={paused}
                title="Workflow paused"
                description="This run needs human approval to continue."
                onResume={() => resume(true)}
                onClose={() => {}}
            />

            {paused && pauseInterrupt && (
                <div
                    style={{
                        position: "fixed",
                        bottom: 12,
                        left: 12,
                        width: 520,
                        maxWidth: "calc(100vw - 24px)",
                        background: "#fff",
                        border: "1px solid #eee",
                        borderRadius: 12,
                        padding: 12,
                    }}
                >
                    <div style={{ fontSize: 12, color: "#666" }}>interrupt</div>
                    <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, margin: "8px 0 0 0" }}>
            {interruptText}
          </pre>
                </div>
            )}
        </div>
    );
}
