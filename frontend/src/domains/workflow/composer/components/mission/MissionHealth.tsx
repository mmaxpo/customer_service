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

function statusLabel(score: number) {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Good";
  if (score >= 50) return "Needs attention";
  return "Blocked";
}

function badgeClass(level: string) {
  if (level === "error") return "bg-red-50 text-red-700 border-red-100";
  if (level === "warning") return "bg-amber-50 text-amber-700 border-amber-100";
  return "bg-slate-50 text-slate-600 border-slate-100";
}

export default function MissionHealth({ nodes, edges }: Props) {
  const health = analyzeMission(nodes, edges);
  const topIssues = health.issues.slice(0, 4);

  return (
    <section className="mb-4 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm shadow-slate-200/70">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 p-4">
        <div>
          <div className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
            Mission Health
          </div>
          <div className="mt-1 text-lg font-extrabold tracking-tight text-slate-950">
            {statusLabel(health.score)}
          </div>
        </div>

        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-950 text-lg font-extrabold text-white">
          {health.score}
        </div>
      </div>

      <div className="space-y-2 p-4">
        {topIssues.length === 0 ? (
          <div className="rounded-2xl bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">
            Mission looks ready. It has a start, connected steps, and an output.
          </div>
        ) : (
          topIssues.map((issue, index) => (
            <div
              key={`${issue.title}-${index}`}
              className={["rounded-2xl border p-3", badgeClass(issue.level)].join(" ")}
            >
              <div className="text-sm font-extrabold">{issue.title}</div>
              <div className="mt-1 text-xs leading-5 opacity-80">
                {issue.description}
              </div>
            </div>
          ))
        )}

        {health.issues.length > topIssues.length && (
          <div className="text-xs font-semibold text-slate-400">
            +{health.issues.length - topIssues.length} more issue(s)
          </div>
        )}
      </div>
    </section>
  );
}
