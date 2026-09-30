export type WorkflowExecutionLike = {
  result?: unknown;
  workflow_run_id?: string | null;
  job_id?: string | null;
  trigger_event_type?: string | null;
  workflow_name?: string | null;
};

export type WorkflowWaitLike = {
  workflow_run_id?: string | null;
  context?: Record<string, unknown> | null;
};

export function readContextValue(context: Record<string, unknown> | null | undefined, key: string) {
  const value = context?.[key];
  if (value === null || value === undefined) return null;
  return String(value);
}

export function nestedRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function workflowExecutionResult(execution: WorkflowExecutionLike) {
  const result = nestedRecord(execution.result);
  const executionResult = nestedRecord(result?.execution_result);
  return executionResult;
}

export function workflowExecutionRealJobId(execution: WorkflowExecutionLike) {
  const executionResult = workflowExecutionResult(execution);
  return String(executionResult?.job_id || execution.workflow_run_id || execution.job_id || "");
}

export function workflowExecutionRequiresApproval(execution: WorkflowExecutionLike) {
  const executionResult = workflowExecutionResult(execution);
  return Boolean(executionResult?.requires_human_approval);
}

export function workflowExecutionActionLabel(execution: WorkflowExecutionLike) {
  const executionResult = workflowExecutionResult(execution);
  return String(
    executionResult?.shopify_action ||
      executionResult?.type ||
      execution.trigger_event_type ||
      execution.workflow_name ||
      "workflow",
  ).replaceAll("_", " ");
}

export function workflowWaitForExecution(
  execution: WorkflowExecutionLike,
  waits: WorkflowWaitLike[],
) {
  const realJobId = workflowExecutionRealJobId(execution);

  return waits.find((wait) => {
    const context = wait.context ?? {};
    const contextJobId = readContextValue(context, "job_id");
    const contextWorkflowRunId = readContextValue(context, "workflow_run_id");
    const contextCorrelationId = readContextValue(context, "correlation_id");

    return (
      wait.workflow_run_id === execution.workflow_run_id ||
      wait.workflow_run_id === realJobId ||
      contextJobId === execution.job_id ||
      contextJobId === realJobId ||
      contextWorkflowRunId === execution.workflow_run_id ||
      contextWorkflowRunId === realJobId ||
      contextCorrelationId === execution.workflow_run_id ||
      contextCorrelationId === realJobId
    );
  });
}
