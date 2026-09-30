"use client";

type Props = {
  nodesCount: number;
  edgesCount: number;
};

export default function MissionMapOverlay({
  nodesCount,
  edgesCount,
}: Props) {
  return (
    <div className="pointer-events-none absolute left-5 top-5 z-10 max-w-sm rounded-3xl border border-white/80 bg-white/90 p-4 shadow-xl shadow-tajeran-100/60 backdrop-blur">
      <div className="text-xs font-extrabold uppercase tracking-wide text-tajeran-700">
        Mission Map
      </div>

      <div className="mt-1 text-lg font-extrabold tracking-tight text-slate-950">
        Build an AI workforce visually
      </div>

      <div className="mt-2 text-xs leading-5 text-slate-500">
        Connect agents, tools, knowledge, decisions, approvals, and outputs into one controlled mission.
      </div>

      <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-bold">
        <span className="rounded-full bg-tajeran-50 px-2.5 py-1 text-tajeran-700">
          {nodesCount} steps
        </span>
        <span className="rounded-full bg-ai-50 px-2.5 py-1 text-ai-700">
          {edgesCount} paths
        </span>
        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700">
          100% controlled
        </span>
      </div>
    </div>
  );
}
