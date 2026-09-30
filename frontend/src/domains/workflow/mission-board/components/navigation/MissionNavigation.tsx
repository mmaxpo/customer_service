"use client";

import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";
import type { MissionBoardView } from "@/domains/workflow/mission-board/types/mission-board";

const items: Array<{ id: MissionBoardView; label: string; description: string }> = [
  { id: "mission", label: "Mission", description: "Summary and purpose" },
  { id: "architecture", label: "Architecture", description: "Structure and quality" },
  { id: "execution", label: "Execution", description: "Runtime timeline" },
  { id: "variables", label: "Variables", description: "State and data" },
  { id: "knowledge", label: "Knowledge", description: "Sources and memory" },
  { id: "tools", label: "Tools", description: "Capabilities" },
  { id: "agents", label: "Agents", description: "AI workforce" },
  { id: "snapshots", label: "Snapshots", description: "Versions and state" },
  { id: "replay", label: "Replay", description: "Debug history" },
];

export function MissionNavigation() {
  const activeView = useMissionBoardStore((state) => state.activeView);
  const setActiveView = useMissionBoardStore((state) => state.setActiveView);

  return (
    <aside className="w-72 border-r border-slate-800 bg-slate-900 p-5">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
          Mission Board
        </div>

        <div className="mt-2 text-2xl font-bold text-white">
          Control Room
        </div>

        <p className="mt-2 text-xs leading-5 text-slate-500">
          Navigate every dimension of the mission.
        </p>
      </div>

      <nav className="space-y-2">
        {items.map((item) => {
          const active = activeView === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={[
                "w-full rounded-2xl px-3 py-3 text-left transition",
                active
                  ? "bg-white text-slate-950 shadow-lg shadow-black/20"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white",
              ].join(" ")}
            >
              <div className="text-sm font-extrabold">{item.label}</div>
              <div
                className={[
                  "mt-0.5 text-xs",
                  active ? "text-slate-500" : "text-slate-500",
                ].join(" ")}
              >
                {item.description}
              </div>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
