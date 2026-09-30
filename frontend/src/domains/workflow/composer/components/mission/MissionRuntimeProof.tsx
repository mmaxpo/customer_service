"use client";

import { useRunStore } from "@/domains/workflow/runner/store/runStore";

type Props = {
  runStatus: string;
  workflowRunId: string;
  runAnswer: string;
};

function shortId(value: string) {
  if (!value) return "";
  return value.length > 12 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

function eventLabel(event: Record<string, any>) {
  const type = event.event || "event";

  const labels: Record<string, string> = {
    run_start: "Mission started",
    run_end: "Mission completed",
    run_failed: "Mission failed",
    run_paused: "Waiting for approval",
    node_start: "Step started",
    node_end: "Step completed",
    node_error: "Step failed",
    node_failed: "Step failed",
  };

  return labels[type] || type;
}

export default function MissionRuntimeProof({
  runStatus,
  workflowRunId,
  runAnswer,
}: Props) {
  const events = useRunStore((state) => state.events);
  const liveStatus = useRunStore((state) => state.status);
  const latestEvents = [...events].slice(-8).reverse();

  return (
    <section className="mb-4 overflow-hidden rounded-3xl border border-ai-100 bg-white shadow-sm shadow-ai-100/70">
      <div className="bg-gradient-to-br from-ai-800 to-slate-950 p-4 text-white">
        <div className="text-xs font-bold uppercase tracking-wide text-ai-100">
          Runtime Proof
        </div>
        <div className="mt-1 text-lg font-extrabold tracking-tight">
          Live mission execution
        </div>
        <div className="mt-2 text-xs leading-5 text-ai-100">
          This area will show agent thinking, tool calls, approvals, state changes, and final result.
        </div>
      </div>

      <div className="space-y-3 p-4">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
            Current status
          </div>
          <div className="mt-1 text-sm font-extrabold text-slate-950">
            {liveStatus !== "unknown" ? liveStatus : runStatus || "Mission not run yet"}
          </div>
          {workflowRunId && (
            <div className="mt-1 text-xs font-semibold text-slate-500">
              Run ID: {shortId(workflowRunId)}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-3">
          <div className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
            Live execution events
          </div>

          {latestEvents.length > 0 ? (
            <div className="mt-3 space-y-2">
              {latestEvents.map((item) => {
                const event = item.event || {};
                return (
                  <div
                    key={item.seq}
                    className="rounded-2xl bg-slate-50 px-3 py-2 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-extrabold text-slate-800">
                        {eventLabel(event)}
                      </span>
                      <span className="font-semibold text-slate-400">
                        seq {item.seq}
                      </span>
                    </div>

                    {(event.node_id || event.node_type) && (
                      <div className="mt-1 text-slate-500">
                        {event.node_id || "node"} {event.node_type ? `• ${event.node_type}` : ""}
                      </div>
                    )}

                    {event.error && (
                      <div className="mt-1 whitespace-pre-wrap text-red-600">
                        {event.error}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="mt-2 text-sm leading-6 text-slate-500">
              Run the mission to see proof of what happened.
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-3">
          <div className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
            Final result
          </div>

          {runAnswer ? (
            <div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">
              {runAnswer}
            </div>
          ) : (
            <div className="mt-2 text-sm leading-6 text-slate-500">
              The mission has not produced a final result yet.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
