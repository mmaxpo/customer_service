"use client";

import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";

const VIEW_LABELS = {
  mission: "Mission Overview",
  architecture: "Architecture Graph",
  execution: "Execution Runtime",
  variables: "Variable Explorer",
  knowledge: "Knowledge Flow",
  tools: "Tool Network",
  agents: "Agent Workforce",
  snapshots: "Snapshots",
  replay: "Replay Studio",
};

export function MissionCommandBar() {
  const activeView = useMissionBoardStore((state) => state.activeView);
  const template = useMissionBoardStore((state) => state.template);
const missionRun = useMissionBoardStore((state) => state.missionRun);
const session = useMissionBoardStore((state) => state.session);

const shortRunId = missionRun?.workflowRunId
  ? missionRun.workflowRunId.length > 14
    ? `${missionRun.workflowRunId.slice(0, 8)}…${missionRun.workflowRunId.slice(-4)}`
    : missionRun.workflowRunId
  : null;

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900 px-5">
      <div>
        <div className="text-xs font-extrabold uppercase tracking-wide text-tajeran-300">
          Tajeran Mission Board
        </div>
        <div className="mt-0.5 text-sm font-bold text-white">
          {template?.name || VIEW_LABELS[activeView]}
        </div>
        {template?.name && (
          <div className="mt-0.5 text-xs font-semibold text-slate-500">
            {VIEW_LABELS[activeView]}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300 hover:bg-slate-800 hover:text-white">
          Search mission
        </button>

        <button className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300 hover:bg-slate-800 hover:text-white">
          Compare
        </button>

        <a
          href="/app/workflows/builder"
          className="rounded-xl bg-white px-3 py-2 text-xs font-extrabold text-slate-950 hover:bg-slate-100"
        >
          Open Builder
        </a>
      </div>
    </header>
  );
}
