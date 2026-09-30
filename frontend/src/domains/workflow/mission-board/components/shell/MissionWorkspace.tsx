"use client";

import { MissionNavigation } from "../navigation/MissionNavigation";
import { MissionCenter } from "../center/MissionCenter";
import { MissionInspector } from "../inspector/MissionInspector";
import { MissionBottomPanel } from "../bottom/MissionBottomPanel";
import { MissionCommandBar } from "./MissionCommandBar";
import { MissionExecutionProvider } from "../runtime/MissionExecutionProvider";

export function MissionWorkspace() {
  return (
    <MissionExecutionProvider>
      <div className="flex h-full flex-col bg-slate-950">

      <MissionCommandBar />

      <div className="flex min-h-0 flex-1">

        <MissionNavigation />

        <MissionCenter />

        <MissionInspector />

      </div>

      <MissionBottomPanel />

      </div>
    </MissionExecutionProvider>
  );
}
