"use client";

import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";

const INSPECTOR_COPY = {
  mission: {
    title: "Mission Inspector",
    sections: [
      ["Purpose", "What the mission is designed to accomplish."],
      ["Health", "Current trust, quality, and readiness."],
      ["Outcome", "Expected business result."],
    ],
  },
  architecture: {
    title: "Architecture Inspector",
    sections: [
      ["Responsibilities", "How work is divided between agents and tools."],
      ["Risks", "Weak paths, duplicated logic, missing outputs."],
      ["Suggestions", "Recommended architecture improvements."],
    ],
  },
  execution: {
    title: "Execution Inspector",
    sections: [
      ["Current run", "Live run status and selected event."],
      ["Approvals", "Human waits and control points."],
      ["Failures", "Errors, retries, and recovery paths."],
    ],
  },
  variables: {
    title: "Variable Inspector",
    sections: [
      ["Created by", "Which node produced the value."],
      ["Read by", "Which downstream steps consume it."],
      ["History", "How the value changed over time."],
    ],
  },
  knowledge: {
    title: "Knowledge Inspector",
    sections: [
      ["Sources", "Documents, policies, and memory used."],
      ["Coverage", "Whether the mission has enough knowledge."],
      ["Gaps", "Missing context or weak retrieval areas."],
    ],
  },
  tools: {
    title: "Tool Inspector",
    sections: [
      ["Capability", "What the tool can do."],
      ["Permissions", "What actions are allowed."],
      ["Reliability", "Latency, failures, and retries."],
    ],
  },
  agents: {
    title: "Agent Inspector",
    sections: [
      ["Identity", "Who the agent is in the mission."],
      ["Responsibility", "What the agent must accomplish."],
      ["Performance", "Outputs, confidence, and behavior history."],
    ],
  },
  snapshots: {
    title: "Snapshot Inspector",
    sections: [
      ["Captured state", "Workflow state at a point in time."],
      ["Diff", "What changed between snapshots."],
      ["Replay anchor", "Where replay can restart."],
    ],
  },
  replay: {
    title: "Replay Inspector",
    sections: [
      ["Cursor", "Current replay position."],
      ["Side effects", "Protected actions during replay."],
      ["Comparison", "Expected vs actual behavior."],
    ],
  },
};

export function MissionInspector() {
  const activeView = useMissionBoardStore((state) => state.activeView);
  const selection = useMissionBoardStore((state) => state.selection);
  const session = useMissionBoardStore((state) => state.session);
  const copy = INSPECTOR_COPY[activeView];

  return (
    <aside className="w-96 border-l border-slate-800 bg-slate-900 p-6">
      <div className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
        Inspector
      </div>

      <div className="mt-2 text-xl font-extrabold text-white">
        {copy.title}
      </div>

      {session && (
        <section className="mt-6 rounded-3xl border border-ai-800 bg-ai-950/30 p-4">
          <div className="text-xs font-extrabold uppercase tracking-wide text-ai-300">
            Session Context
          </div>

          <div className="mt-3 space-y-2 text-xs">
            <Row label="Run" value={session.workflowRunId} />
            <Row label="Conversation" value={session.conversationId} />
            <Row label="Customer" value={session.customerId} />
            <Row label="Channel" value={session.channel} />
          </div>
        </section>
      )}

      {selection?.type === "entity" && (
        <section className="mt-6 rounded-3xl border border-tajeran-300 bg-slate-950 p-4">
          <div className="text-xs font-extrabold uppercase tracking-wide text-tajeran-300">
            Selected {selection.entityType}
          </div>
          <div className="mt-2 text-xl font-extrabold text-white">
            {selection.label}
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            {selection.description}
          </p>
        </section>
      )}

      {selection?.type === "relationship" && (
        <section className="mt-6 rounded-3xl border border-cyan-300 bg-slate-950 p-4">
          <div className="text-xs font-extrabold uppercase tracking-wide text-cyan-300">
            Relationship
          </div>

          <div className="mt-3 space-y-3">
            <div className="rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2">
              <div className="text-xs text-slate-500">Source</div>
              <div className="font-extrabold text-white">{selection.source}</div>
            </div>

            <div className="rounded-full bg-cyan-950 px-3 py-2 text-xs font-extrabold uppercase tracking-wide text-cyan-200">
              {selection.label}
            </div>

            <div className="rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2">
              <div className="text-xs text-slate-500">Target</div>
              <div className="font-extrabold text-white">{selection.target}</div>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            <section className="rounded-2xl border border-slate-700 bg-slate-900 p-3">
              <div className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
                Why this exists
              </div>
              <p className="mt-2 text-xs leading-6 text-slate-400">
                This relationship explains how one mission concept depends on another. It is not only a line — it is the reason intelligence moves from source to target.
              </p>
            </section>

            <section className="rounded-2xl border border-slate-700 bg-slate-900 p-3">
              <div className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
                What likely flows here
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {["context", "decision", "tool result", "confidence"].map((item) => (
                  <span
                    key={item}
                    className="rounded-full bg-slate-950 px-2 py-1 text-[10px] font-bold text-slate-400"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-700 bg-slate-900 p-3">
              <div className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
                What can fail
              </div>
              <p className="mt-2 text-xs leading-6 text-slate-400">
                Missing input, weak confidence, tool failure, rejected approval, or an output that downstream agents cannot use.
              </p>
            </section>

            <section className="rounded-2xl border border-dashed border-cyan-800 bg-cyan-950/20 p-3">
              <div className="text-xs font-extrabold uppercase tracking-wide text-cyan-300">
                Runtime proof coming
              </div>
              <p className="mt-2 text-xs leading-6 text-cyan-100/70">
                Later this relationship will show live events, variables crossing this edge, replay history, failures, and AI reasoning evidence.
              </p>
            </section>
          </div>
        </section>
      )}

      <div className="mt-6 space-y-3">
        {copy.sections.map(([title, description]) => (
          <section
            key={title}
            className="rounded-2xl border border-slate-800 bg-slate-950 p-4"
          >
            <div className="text-sm font-extrabold text-white">{title}</div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              {description}
            </p>
          </section>
        ))}
      </div>
    </aside>
  );
}


function Row({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950 px-3 py-2">
      <span className="font-bold text-slate-500">{label}</span>
      <span className="truncate font-extrabold text-white">{value || "—"}</span>
    </div>
  );
}
