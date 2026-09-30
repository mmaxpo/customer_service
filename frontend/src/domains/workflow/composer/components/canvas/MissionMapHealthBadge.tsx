"use client";

import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";
import { analyzeMission } from "@/domains/workflow/composer/utils/analyzeMission";

type Props = {
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
};

function status(score: number) {
  if (score >= 90) return "Ready";
  if (score >= 75) return "Good";
  if (score >= 50) return "Needs review";
  return "Blocked";
}

function tone(score: number) {
  if (score >= 90) return "border-emerald-100 bg-emerald-50 text-emerald-700";
  if (score >= 75) return "border-ai-100 bg-ai-50 text-ai-700";
  if (score >= 50) return "border-amber-100 bg-amber-50 text-amber-700";
  return "border-red-100 bg-red-50 text-red-700";
}

export default function MissionMapHealthBadge({ nodes, edges }: Props) {
  const health = analyzeMission(nodes, edges);

  return (
    <div className="pointer-events-none absolute right-5 top-5 z-10 rounded-3xl border border-white/80 bg-white/90 p-3 shadow-xl shadow-slate-200/70 backdrop-blur">
      <div className="text-[10px] font-extrabold uppercase tracking-wide text-slate-400">
        Mission Health
      </div>

      <div className="mt-2 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-950 text-sm font-extrabold text-white">
          {health.score}
        </div>

        <div>
          <div className={["rounded-full border px-2.5 py-1 text-xs font-extrabold", tone(health.score)].join(" ")}>
            {status(health.score)}
          </div>
          <div className="mt-1 text-[10px] font-semibold text-slate-400">
            {health.issues.length || "No"} issue(s)
          </div>
        </div>
      </div>
    </div>
  );
}
