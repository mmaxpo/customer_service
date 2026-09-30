"use client";

import { useSearchParams } from "next/navigation";

import { MissionBoardEmptyState } from "@/domains/workflow/mission-board/components/empty/MissionBoardEmptyState";
import { MissionRunLoader } from "@/domains/workflow/mission-board/components/runtime/MissionRunLoader";
import { MissionTemplateLoader } from "@/domains/workflow/mission-board/components/shell/MissionTemplateLoader";
import { MissionWorkspace } from "@/domains/workflow/mission-board/components/shell/MissionWorkspace";

export default function MissionBoardPage() {
  const searchParams = useSearchParams();
  const templateId = searchParams.get("templateId");
  const runId = searchParams.get("runId");
  const conversationId = searchParams.get("conversationId");

  if (!templateId && !runId) {
    return <MissionBoardEmptyState />;
  }

  return (
    <>
      <MissionTemplateLoader templateId={templateId} />
      <MissionRunLoader
        runId={runId}
        conversationId={conversationId}
        templateId={templateId}
      />
      <MissionWorkspace />
    </>
  );
}
