"use client";

import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";
import { MissionKnowledgeGraphView } from "@/domains/workflow/mission-board/graph/MissionKnowledgeGraphView";
import { MissionLiveFlow } from "../live/MissionLiveFlow";
import { MissionStory } from "../story/MissionStory";

const VIEW_COPY = {
  mission: {
    title: "Mission Overview",
    description: "Purpose, goals, health, and current operational confidence.",
  },
  architecture: {
    title: "Architecture Graph",
    description: "Structure, responsibilities, dependencies, and mission quality.",
  },
  execution: {
    title: "Execution View",
    description: "Live runtime, timeline, events, approvals, and tool calls.",
  },
  variables: {
    title: "Variable Explorer",
    description: "Inspect mission state, variables, outputs, and mutations.",
  },
  knowledge: {
    title: "Knowledge Flow",
    description: "Understand what each agent knew, searched, and used.",
  },
  tools: {
    title: "Tool Network",
    description: "External systems, permissions, tool calls, latency, and failures.",
  },
  agents: {
    title: "Agent Workforce",
    description: "Inspect each agent identity, role, tools, memory, and performance.",
  },
  snapshots: {
    title: "Snapshots",
    description: "Captured mission states, versioned runtime context, and comparisons.",
  },
  replay: {
    title: "Replay Studio",
    description: "Replay missions step by step to debug and improve behavior.",
  },
};

export function MissionCenter() {
  const activeView = useMissionBoardStore((state) => state.activeView);
  const copy = VIEW_COPY[activeView];

  return (
    <main className="min-w-0 flex-1 bg-slate-950 p-5">
      <section className="flex h-full flex-col overflow-hidden rounded-[32px] border border-slate-800 bg-slate-900 shadow-2xl shadow-black/30">
        <div className="border-b border-slate-800 px-6 py-4">
          <div className="text-xs font-extrabold uppercase tracking-wide text-tajeran-300">
            {activeView}
          </div>

          <div className="mt-1 text-2xl font-extrabold tracking-tight text-white">
            {copy.title}
          </div>

          <p className="mt-1 text-sm leading-6 text-slate-400">
            {copy.description}
          </p>
        </div>

        <div className="min-h-0 flex-1">
          {activeView === "mission" ? (
            <>
              <MissionStory />

              <div className="mt-6">
                <MissionLiveFlow />
              </div>

              <details className="mt-6 rounded-[28px] border border-slate-800 bg-slate-950">
                <summary className="cursor-pointer px-6 py-5 text-sm font-extrabold text-slate-300">
                  Advanced Mission Graph
                </summary>

                <MissionKnowledgeGraphView />
              </details>
            </>
          ) : (
            <div className="flex h-full items-center justify-center p-8">
              <div className="max-w-xl text-center">
                <div className="text-5xl font-black tracking-tight text-white">
                  {copy.title}
                </div>

                <p className="mt-4 text-base leading-7 text-slate-500">
                  This region will become the main visualization canvas for {copy.title.toLowerCase()}.
                </p>

                <div className="mt-8 rounded-3xl border border-dashed border-slate-700 bg-slate-950 p-8 text-sm font-semibold text-slate-500">
                  Visualization module placeholder
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
