from __future__ import annotations

from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.compiler.execution_ir.models import ExecutionGraph
from app.tcos.execution.adapters import RuntimeExecutionAdapter, WorkflowRuntimeAdapter

from .models import (
    ExecutionBackend,
    ExecutionSession,
    ExecutionStatus,
)


class ExecutionCoordinator:
    """
    Prepares compiled Execution IR for Runtime and coordinates execution.
    """

    def prepare(
        self,
        execution_graph: ExecutionGraph,
        *,
        backend: ExecutionBackend = ExecutionBackend.WORKFLOW_RUNTIME,
    ) -> ExecutionSession:

        session = ExecutionSession(
            backend=backend,
            execution_graph=execution_graph.model_dump(mode="json"),
        )

        session.record(
            "ExecutionPreparationStarted",
            backend=backend.value,
        )

        workflow = execution_graph_to_runtime_workflow(execution_graph)

        session.runtime_workflow = workflow
        session.status = ExecutionStatus.COMPLETED

        session.record(
            "RuntimeWorkflowPrepared",
            node_count=len(workflow["nodes"]),
            edge_count=len(workflow["edges"]),
        )

        session.metrics = {
            "node_count": len(workflow["nodes"]),
            "edge_count": len(workflow["edges"]),
        }

        return session

    async def execute(
        self,
        execution_graph: ExecutionGraph,
        *,
        ctx,
        message: str,
        strict: bool = True,
        backend: ExecutionBackend = ExecutionBackend.WORKFLOW_RUNTIME,
        adapter: RuntimeExecutionAdapter | None = None,
    ) -> ExecutionSession:
        session = self.prepare(
            execution_graph,
            backend=backend,
        )

        session.status = ExecutionStatus.RUNNING
        session.record(
            "RuntimeExecutionStarted",
            backend=backend.value,
        )

        runtime_adapter = adapter or WorkflowRuntimeAdapter()

        try:
            result = await runtime_adapter.execute(
                workflow=session.runtime_workflow or {},
                message=message,
                ctx=ctx,
                strict=strict,
            )
        except Exception as exc:
            session.status = ExecutionStatus.FAILED
            session.runtime_result = {
                "error": str(exc),
            }
            session.record(
                "RuntimeExecutionFailed",
                error=str(exc),
            )
            return session

        session.runtime_result = result
        session.status = ExecutionStatus.COMPLETED
        session.record(
            "RuntimeExecutionCompleted",
            status=(result.get("meta") or {}).get("status"),
        )
        session.metrics.update(
            {
                "runtime_status": (result.get("meta") or {}).get("status"),
            }
        )

        return session
