"use client";

import { useEffect } from "react";

import { useRunHydration } from "@/domains/workflow/runner/hooks/useRunHydration";
import { useRunStream } from "@/domains/workflow/runner/hooks/useRunStream";
import { useRunStore } from "@/domains/workflow/runner/store/runStore";
import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";

type Props = {
  runId: string | null;
  conversationId?: string | null;
  templateId?: string | null;
};

export function MissionRunLoader({
  runId,
  conversationId = null,
  templateId = null,
}: Props) {
  const setRunId = useRunStore((state) => state.setRunId);

  const setSession = useMissionBoardStore((s) => s.setSession);

  useEffect(() => {
    if (!runId) return;

    setRunId(runId);

    setSession({
      workflowRunId: runId,
      workflowTemplateId: templateId,
      conversationId,
      customerId: null,
      channel: null,
      missionName: null,
      startedAt: new Date().toISOString(),
    });
  }, [runId, conversationId, templateId, setRunId, setSession]);

  useRunHydration(runId);
  useRunStream(runId);

  return null;
}
