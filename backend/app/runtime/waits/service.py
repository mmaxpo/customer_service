from __future__ import annotations

from app.workflow_operations.waits.schemas import WorkflowWaitCreate
from app.workflow_operations.waits.service import WorkflowWaitService


async def create_runtime_wait(
    *,
    ctx,
    workflow_run_id: str,
    node_id: str | None,
    wait,
):
    if ctx.db is None:
        raise ValueError("Durable workflow waits require ctx.db")

    return await WorkflowWaitService(ctx.db).create(
        user_id=ctx.user_id,
        payload=WorkflowWaitCreate(
            workflow_run_id=str(workflow_run_id),
            node_id=node_id,
            wait_type=wait.wait_type,
            payload=wait.payload,
            expires_at=wait.expires_at,
        ),
    )
