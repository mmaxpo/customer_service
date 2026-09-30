from __future__ import annotations

from typing import Protocol


class RuntimeExecutionAdapter(Protocol):
    async def execute(
        self,
        *,
        workflow: dict,
        message: str,
        ctx,
        strict: bool = True,
    ) -> dict: ...


class WorkflowRuntimeAdapter:
    async def execute(
        self,
        *,
        workflow: dict,
        message: str,
        ctx,
        strict: bool = True,
    ) -> dict:
        from app.runtime.engine.executor import execute_workflow_dag

        return await execute_workflow_dag(
            ctx=ctx,
            workflow=workflow,
            message=message,
            strict=strict,
        )
