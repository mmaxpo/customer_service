export type MissionNodeExecutionState =
  | "idle"
  | "running"
  | "done"
  | "failed"
  | "paused";

export type MissionRunNode = {
  id: string;
  status: MissionNodeExecutionState;
};

export type MissionRun = {
  workflowRunId: string | null;
  status: string;
  nodes: MissionRunNode[];
};
