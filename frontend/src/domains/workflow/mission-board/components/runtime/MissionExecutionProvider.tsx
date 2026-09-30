"use client";

import { useEffect, useMemo } from "react";

import { useRunStore } from "@/domains/workflow/runner/store/runStore";
import { buildMissionRun } from "@/domains/workflow/mission-board/runtime/buildMissionRun";
import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";

type Props = {
  children: React.ReactNode;
};

export function MissionExecutionProvider({ children }: Props) {
  const workflowRunId = useRunStore((state) => state.runId);
  const workflow = useRunStore((state) => state.workflow);
  const status = useRunStore((state) => state.status);
  const nodeStatus = useRunStore((state) => state.nodeStatus);

  const setMissionRun = useMissionBoardStore((state) => state.setMissionRun);

  const missionRun = useMemo(
    () =>
      buildMissionRun({
        workflowRunId,
        workflow,
        status,
        nodeStatus,
      }),
    [workflowRunId, workflow, status, nodeStatus],
  );

  useEffect(() => {
    setMissionRun(missionRun);
  }, [missionRun, setMissionRun]);

  return <>{children}</>;
}
