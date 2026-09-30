"use client";

import { useEffect } from "react";
import { useRunStore } from "../store/runStore";

const TERMINAL_EVENTS = new Set(["run_end", "run_failed", "run_cancelled"]);

export function useRunStream(runId: string | null) {
    const pushEvent = useRunStore((s) => s.pushEvent);

    useEffect(() => {
        if (!runId) return;

        let closed = false;

        const streamUrl = new URL(
            `/api/workflows/runs/${runId}/stream?after_seq=0`,
            window.location.origin
        );

        console.log("Workflow SSE URL", streamUrl.toString());

        const es = new EventSource(streamUrl.toString(), {
            withCredentials: true,
        });

        const close = () => {
            if (closed) return;
            closed = true;
            es.close();
        };

        const handleRunEvent = (msg: MessageEvent) => {
            try {
                const payload = JSON.parse(msg.data);
                pushEvent(payload);

                const eventType = payload?.event?.event;
                if (TERMINAL_EVENTS.has(eventType)) {
                    close();
                }
            } catch (err) {
                console.error("Failed to parse workflow SSE event", err);
            }
        };

        es.addEventListener("run_event", handleRunEvent);

        es.addEventListener("heartbeat", () => {
            // keep-alive only
        });

        es.onerror = () => {
            // EventSource fires error when backend closes a completed stream.
            // Close it so browser does not reconnect forever.
            close();
        };

        return () => {
            es.removeEventListener("run_event", handleRunEvent);
            close();
        };
    }, [runId, pushEvent]);
}