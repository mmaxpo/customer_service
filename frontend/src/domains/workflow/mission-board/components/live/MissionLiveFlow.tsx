"use client";

import { useMemo } from "react";

import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";

const COLORS = {
  idle: "border-slate-700 bg-slate-900 text-slate-400",
  running: "border-cyan-400 bg-cyan-950 text-cyan-200 animate-pulse",
  done: "border-emerald-400 bg-emerald-950 text-emerald-200",
  failed: "border-red-400 bg-red-950 text-red-200",
  paused: "border-amber-400 bg-amber-950 text-amber-200",
};

export function MissionLiveFlow() {
  const missionRun = useMissionBoardStore((s) => s.missionRun);

  const steps = useMemo(
    () => missionRun?.nodes ?? [],
    [missionRun],
  );

  return (
    <section className="rounded-[32px] border border-slate-800 bg-slate-950 p-6">
      <div className="text-xs font-extrabold uppercase tracking-[0.25em] text-tajeran-300">
        Live Mission
      </div>

      <div className="mt-2 text-2xl font-black text-white">
        AI is executing this mission
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-4">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center gap-4">
            <div
              className={[
                "min-w-[160px] rounded-3xl border px-4 py-4 transition-all",
                COLORS[step.status],
              ].join(" ")}
            >
              <div className="text-[10px] font-extrabold uppercase tracking-wide opacity-60">
                Step {index + 1}
              </div>

              <div className="mt-2 truncate font-black">
                {step.id}
              </div>

              <div className="mt-3 text-xs font-bold uppercase">
                {step.status}
              </div>
            </div>

            {index < steps.length - 1 && (
              <div className="h-[2px] w-10 bg-slate-700" />
            )}
          </div>
        ))}

        {steps.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-700 p-6 text-slate-500">
            Waiting for a real workflow execution...
          </div>
        )}
      </div>
    </section>
  );
}
