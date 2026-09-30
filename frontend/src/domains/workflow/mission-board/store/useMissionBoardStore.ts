"use client";

import { create } from "zustand";
import type { MissionBoardView } from "@/domains/workflow/mission-board/types/mission-board";
import type { WorkflowTemplate } from "@/domains/customer-service/api/customer-service";
import type { MissionRun } from "@/domains/workflow/mission-board/runtime/missionRunTypes";
import type { MissionSession } from "@/domains/workflow/mission-board/session/missionSession";

type MissionBoardSelection =
| {
  type: "entity";
  id: string;
  label: string;
  entityType: string;
  description: string;
}
| {
  type: "relationship";
  id: string;
  label: string;
  source: string;
  target: string;
}
| null;

type MissionBoardState = {
  activeView: MissionBoardView;
  setActiveView: (view: MissionBoardView) => void;

  selection: MissionBoardSelection;
  setSelection: (selection: MissionBoardSelection) => void;

  template: WorkflowTemplate | null;
  setTemplate: (template: WorkflowTemplate | null) => void;

  missionRun: MissionRun | null;
  setMissionRun: (missionRun: MissionRun | null) => void;

  session: MissionSession | null;
  setSession: (session: MissionSession | null) => void;
};

export const useMissionBoardStore = create<MissionBoardState>((set) => ({
  activeView: "mission",
  setActiveView: (view) => set({ activeView: view }),

  selection: null,
  setSelection: (selection) => set({ selection }),

  template: null,
  setTemplate: (template) => set({ template }),

  missionRun: null,
  setMissionRun: (missionRun) => set({ missionRun }),

  session: null,
  setSession: (session) => set({ session }),
}));
