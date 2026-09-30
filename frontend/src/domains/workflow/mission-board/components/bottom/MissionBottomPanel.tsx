"use client";

import { useMemo } from "react";

import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";

export function MissionBottomPanel() {
  const missionRun = useMissionBoardStore((state) => state.missionRun);

  const summary = useMemo(() => {
    const nodes = missionRun?.nodes ?? [];

    return {
      total: nodes.length,
      running: nodes.filter((n) => n.status === "running").length,
      done: nodes.filter((n) => n.status === "done").length,
      failed: nodes.filter((n) => n.status === "failed").length,
      paused: nodes.filter((n) => n.status === "paused").length,
      idle: nodes.filter((n) => n.status === "idle").length,
    };
  }, [missionRun]);

  return (
    <footer className="border-t border-slate-800 bg-slate-950 px-6 py-4">
      <div className="grid gap-4 md:grid-cols-7">
        <Card title="Run">
          {missionRun?.workflowRunId
            ? missionRun.workflowRunId.slice(0, 8)
            : "—"}
        </Card>

        <Card title="Status">
          {missionRun?.status ?? "idle"}
        </Card>

        <Card title="Nodes">
          {summary.total}
        </Card>

        <Card title="Running">
          {summary.running}
        </Card>

        <Card title="Done">
          {summary.done}
        </Card>

        <Card title="Paused">
          {summary.paused}
        </Card>

        <Card title="Failed">
          {summary.failed}
        </Card>
      </div>
    </footer>
  );
}

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-3">
      <div className="text-[10px] font-extrabold uppercase tracking-wide text-slate-500">
        {title}
      </div>

      <div className="mt-2 text-lg font-black text-white">
        {children}
      </div>
    </section>
  );
}
