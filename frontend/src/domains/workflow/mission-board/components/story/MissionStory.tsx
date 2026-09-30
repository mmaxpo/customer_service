"use client";

import { useMemo } from "react";
import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";

export function MissionStory() {
  const session = useMissionBoardStore((s) => s.session);
  const missionRun = useMissionBoardStore((s) => s.missionRun);

  const nodes = missionRun?.nodes ?? [];

  const runningNode = useMemo(
    () => nodes.find((n) => n.status === "running"),
    [nodes],
  );

  const completed = nodes.filter((n) => n.status === "done").length;
  const progress =
    nodes.length === 0
      ? 0
      : Math.round((completed / nodes.length) * 100);

  return (
    <section className="rounded-[32px] border border-slate-800 bg-slate-950 p-6">
      <div className="flex items-start justify-between gap-6">

        <div>
          <div className="text-xs font-extrabold uppercase tracking-[0.3em] text-tajeran-300">
            AI Operations
          </div>

          <h2 className="mt-3 text-3xl font-black text-white">
            {session?.missionName ?? "Customer Support Mission"}
          </h2>

          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-400">
            Observe what the AI is doing right now, where it is in the
            mission, and how close it is to serving the customer.
          </p>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900 px-5 py-4">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Progress
          </div>

          <div className="mt-2 text-3xl font-black text-white">
            {progress}%
          </div>
        </div>

      </div>

      <div className="mt-8 h-3 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-4">

        <Info
          title="Customer"
          value={session?.customerId ?? "Unknown"}
        />

        <Info
          title="Conversation"
          value={session?.conversationId ?? "Waiting"}
        />

        <Info
          title="Running Step"
          value={runningNode?.id ?? "Completed"}
        />

        <Info
          title="Runtime"
          value={missionRun?.status ?? "Idle"}
        />

      </div>

      <div className="mt-8 rounded-3xl border border-cyan-800 bg-cyan-950/40 p-5">

        <div className="text-xs font-extrabold uppercase tracking-wide text-cyan-300">
          Current Activity
        </div>

        <div className="mt-3 text-xl font-black text-white">
          {runningNode
            ? `AI is executing "${runningNode.id}"`
            : "Mission completed"}
        </div>

        <div className="mt-3 text-sm leading-7 text-cyan-100">
          {runningNode
            ? "When this finishes, the mission automatically continues to the next step."
            : "The AI finished all mission steps successfully."}
        </div>

      </div>

    </section>
  );
}

function Info({
  title,
  value,
}: {
  title: string;
  value: string;
}) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
        {title}
      </div>

      <div className="mt-2 truncate text-lg font-black text-white">
        {value}
      </div>
    </div>
  );
}
