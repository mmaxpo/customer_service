import type { NodeStatus } from "@/domains/workflow/runner/store/runStore";
import type { MissionRun, MissionNodeExecutionState } from "./missionRunTypes";

function normalizeNodeStatus(status: NodeStatus | undefined): MissionNodeExecutionState {
  if (status === "running") return "running";
  if (status === "done") return "done";
  if (status === "failed") return "failed";
  if (status === "paused") return "paused";

  return "idle";
}

export function buildMissionRun(input: {
  workflowRunId: string | null;
  workflow: any;
  status: string;
  nodeStatus: Record<string, NodeStatus>;
}): MissionRun {
  const nodes = Array.isArray(input.workflow?.nodes)
    ? input.workflow.nodes
    : [];

  return {
    workflowRunId: input.workflowRunId,
    status: input.status,
    nodes: nodes.map((node: any) => ({
      id: String(node.id),
      status: normalizeNodeStatus(input.nodeStatus[String(node.id)]),
    })),
  };
}
