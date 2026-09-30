"use client";

import type { NodeStatus } from "@/domains/workflow/runner/store/runStore";

type Props = {
  nodeStatus: Record<string, NodeStatus>;
};

export default function MissionRuntimeSummary({ nodeStatus }: Props) {
  const values = Object.values(nodeStatus);

  const running = values.filter((value) => value === "running").length;
  const done = values.filter((value) => value === "done").length;
  const failed = values.filter((value) => value === "failed").length;
  const paused = values.filter((value) => value === "paused").length;

  if (values.length === 0) return null;

  return (
    <section className="mb-4 rounded-3xl border border-ai-100 bg-ai-50/50 p-4">
      <div className="text-xs font-extrabold uppercase tracking-wide text-ai-700">
        Live Mission Status
      </div>

      <div className="mt-3 grid grid-cols-4 gap-2 text-center">
        <div className="rounded-2xl bg-white p-2">
          <div className="text-lg font-extrabold text-ai-700">{running}</div>
          <div className="text-[10px] font-bold uppercase text-slate-400">Running</div>
        </div>

        <div className="rounded-2xl bg-white p-2">
          <div className="text-lg font-extrabold text-emerald-700">{done}</div>
          <div className="text-[10px] font-bold uppercase text-slate-400">Done</div>
        </div>

        <div className="rounded-2xl bg-white p-2">
          <div className="text-lg font-extrabold text-amber-700">{paused}</div>
          <div className="text-[10px] font-bold uppercase text-slate-400">Paused</div>
        </div>

        <div className="rounded-2xl bg-white p-2">
          <div className="text-lg font-extrabold text-red-700">{failed}</div>
          <div className="text-[10px] font-bold uppercase text-slate-400">Failed</div>
        </div>
      </div>
    </section>
  );
}
