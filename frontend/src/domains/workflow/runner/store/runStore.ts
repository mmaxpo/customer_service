import { create } from "zustand";

export type RunStatus = "running" | "paused" | "done" | "failed" | "queued" | "unknown";
export type NodeStatus = "idle" | "running" | "done" | "failed" | "paused";

export type RunEventPayload = {
    seq: number;
    event: Record<string, any>;
    created_at?: string | null;
};

export type RunHydration = {
    workflow_run_id: string;
    status: RunStatus;
    thread_id?: string | null;
    workflow: any;
    state: any;
    extra: any;
};

type State = {
    runId: string | null;
    setRunId: (runId: string | null) => void;
    status: RunStatus;
    workflow: any | null;
    state: any | null;
    extra: any | null;

    lastSeq: number;
    events: RunEventPayload[];
    nodeStatus: Record<string, NodeStatus>;
    pauseInterrupt: any | null;

    setHydration: (h: RunHydration) => void;
    pushEvent: (e: RunEventPayload) => void;
    reset: () => void;
};

export const useRunStore = create<State>((set, get) => ({
    runId: null,
    status: "unknown",
    workflow: null,
    state: null,
    extra: null,

    lastSeq: 0,
    events: [],
    nodeStatus: {},
    pauseInterrupt: null,

    setRunId: (runId) =>
        set({
            runId,
            lastSeq: 0,
            events: [],
            nodeStatus: {},
            pauseInterrupt: null,
        }),

    setHydration: (h) =>
        set({
            runId: h.workflow_run_id,
            status: (h.status as RunStatus) ?? "unknown",
            workflow: h.workflow ?? null,
            state: h.state ?? null,
            extra: h.extra ?? null,
            pauseInterrupt: h.extra?.interrupt ?? null,
        }),

    pushEvent: (p) => {
        if (!p || typeof p.seq !== "number") return;
        if (p.seq <= get().lastSeq) return;

        const ev = p.event || {};
        const type = ev.event;
        const nodeId = ev.node_id;

        set((s) => {
            const nodeStatus = { ...s.nodeStatus };
            let status: RunStatus = s.status;
            let pauseInterrupt = s.pauseInterrupt;

            if (type === "node_start" && nodeId) nodeStatus[nodeId] = "running";
            if (type === "node_end" && nodeId) nodeStatus[nodeId] = "done";
            if ((type === "node_failed" || type === "node_error") && nodeId) {
                nodeStatus[nodeId] = "failed";
            }

            if (type === "run_start") status = "running";
            if (type === "run_paused") {
                status = "paused";
                pauseInterrupt = ev.interrupt ?? ev;
            }
            if (type === "run_end") {
                status = "done";
                pauseInterrupt = null;
            }
            if (type === "run_failed") {
                status = "failed";
                pauseInterrupt = null;
            }
            if (type === "run_cancelled") {
                status = "failed";
                pauseInterrupt = null;
            }

            return {
                lastSeq: p.seq,
                events: [...s.events, p],
                nodeStatus,
                status,
                pauseInterrupt,
            };
        });
    },

    reset: () =>
        set({
            runId: null,
            status: "unknown",
            workflow: null,
            state: null,
            extra: null,
            lastSeq: 0,
            events: [],
            nodeStatus: {},
            pauseInterrupt: null,
        }),
}));