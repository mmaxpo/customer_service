"use client";

import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";
import { compileMissionFromTemplate } from "@/domains/workflow/mission-board/compiler/compileMission";
import type { MissionGraphEntityType } from "./graphTypes";

const TYPE_LABEL: Record<MissionGraphEntityType, string> = {
  mission: "Mission",
  agent: "AI Agent",
  tool: "Tool",
  variable: "Data",
  knowledge: "Knowledge",
  decision: "Decision",
  response: "Response",
};

const TYPE_STYLE: Record<MissionGraphEntityType, string> = {
  mission: "border-white bg-white text-slate-950",
  agent: "border-ai-300 bg-ai-950 text-white",
  tool: "border-emerald-300 bg-emerald-950 text-white",
  variable: "border-slate-500 bg-slate-950 text-slate-100",
  knowledge: "border-cyan-300 bg-cyan-950 text-white",
  decision: "border-amber-300 bg-amber-950 text-white",
  response: "border-purple-300 bg-purple-950 text-white",
};

export function MissionKnowledgeGraphView() {
  const template = useMissionBoardStore((state) => state.template);
  const mission = compileMissionFromTemplate(template);
  const missionRun = useMissionBoardStore((state) => state.missionRun);
  const selection = useMissionBoardStore((state) => state.selection);
  const setSelection = useMissionBoardStore((state) => state.setSelection);

  const missionEntity = mission.entities.find((entity) => entity.type === "mission");
  const steps = mission.entities.filter((entity) => entity.type !== "mission");

  const statusForStep = (stepId: string) =>
    missionRun?.nodes.find((node) => node.id === stepId)?.status ?? "idle";

  return (
    <div className="h-full overflow-auto p-6">
      <div className="mx-auto max-w-6xl">
        <section className="mb-5 rounded-[32px] border border-slate-800 bg-slate-950 p-5">
          <div className="text-xs font-extrabold uppercase tracking-wide text-tajeran-300">
            What this mission does
          </div>

          <h2 className="mt-2 text-3xl font-black tracking-tight text-white">
            {missionEntity?.label || mission.name}
          </h2>

          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-400">
            {missionEntity?.description || mission.description}
          </p>

          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <Metric label="Steps" value={steps.length} />
            <Metric label="Agents" value={steps.filter((s) => s.type === "agent").length} />
            <Metric label="Tools" value={steps.filter((s) => s.type === "tool").length} />
            <Metric label="Decisions" value={steps.filter((s) => s.type === "decision").length} />
          </div>
        </section>

        <section className="rounded-[36px] border border-slate-800 bg-slate-950 p-5">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <div className="text-xs font-extrabold uppercase tracking-wide text-tajeran-300">
                Mission flow
              </div>
              <div className="mt-1 text-xl font-extrabold text-white">
                Watch the work from start to finish
              </div>
            </div>

            <div className="rounded-full border border-slate-700 px-3 py-1 text-xs font-bold text-slate-400">
              Click any step to inspect
            </div>
          </div>

          <div className="space-y-3">
            {steps.map((step, index) => {
              const runStatus = statusForStep(step.id);

              return (
              <div key={step.id}>
                <button
                  type="button"
                  onClick={() =>
                    setSelection({
                      type: "entity",
                      id: step.id,
                      label: step.label,
                      entityType: step.type,
                      description: step.description,
                    })
                  }
                  className={[
                    "grid w-full gap-4 rounded-3xl border p-4 text-left shadow-xl shadow-black/20 transition hover:-translate-y-0.5 md:grid-cols-[80px_180px_1fr]",
                    selection?.type === "entity" && selection.id === step.id
                      ? "ring-4 ring-white/40"
                      : "",
                    TYPE_STYLE[step.type],
                  ].join(" ")}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-black/20 text-lg font-black">
                      {runStatus === "done"
                        ? "✓"
                        : runStatus === "running"
                          ? "●"
                          : runStatus === "failed"
                            ? "!"
                            : index + 1}
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] font-extrabold uppercase tracking-wide opacity-60">
                      {TYPE_LABEL[step.type]}
                    </div>
                    <div className="mt-1 text-lg font-black">{step.label}</div>
                    <div className="mt-2 inline-flex rounded-full bg-black/20 px-2 py-1 text-[10px] font-extrabold uppercase tracking-wide">
                      {runStatus}
                    </div>
                  </div>

                  <p className="text-sm leading-6 opacity-75">
                    {step.description}
                  </p>
                </button>

                {index < steps.length - 1 && (
                  <div className="ml-10 h-8 border-l-2 border-dashed border-slate-700" />
                )}
              </div>
              );
            })}
          </div>
        </section>

        <section className="mt-5 rounded-[32px] border border-slate-800 bg-slate-950 p-5">
          <div className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
            Why this matters
          </div>
          <p className="mt-2 text-sm leading-7 text-slate-400">
            This board is meant to show the merchant what the AI is doing: which step is running,
            which tool is called, what data is produced, and where the customer reply comes from.
            The next patches will connect runtime status directly onto these steps.
          </p>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-3">
      <div className="text-[10px] font-extrabold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-black text-white">{value}</div>
    </div>
  );
}
