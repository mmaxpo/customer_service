from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.node_registration import register_application_nodes
from app.platform.jobs.contracts import JobContext
from app.runtime.execution import execute_workflow_dag
from app.runtime.persistence import (
    build_event_sink,
    build_run_store,
)
from app.runtime.tools import build_tools
from app.runtime.workflows import build_runtime_workflow_repository
from app.runtime_services import build_application_runtime_context


def _dummy_request(*, tools=None):
    return SimpleNamespace(
        state=SimpleNamespace(tools=tools),
        app=SimpleNamespace(state=SimpleNamespace(tools=tools)),
    )


def _raise_if_workflow_failed(result: dict) -> None:
    meta = result.get("meta") or {}
    status = str(meta.get("status") or "").lower()

    if status in {
        "error",
        "failed",
        "cancelled",
        "deadlock",
    }:
        raise RuntimeError(
            meta.get("error") or f"Workflow execution failed with status={status}"
        )


async def run_workflow_job(
    payload: dict[str, Any],
    ctx: JobContext,
) -> dict[str, Any]:
    register_application_nodes()

    user_id = ctx.job.user_id or payload.get("user_id")

    if user_id is None:
        raise ValueError("workflow.run job requires user_id")

    workflow = payload.get("workflow")

    workflow_id = payload.get("workflow_id")

    if workflow is None and workflow_id:
        row = await build_runtime_workflow_repository(ctx.db).get(
            user_id=uuid.UUID(str(user_id)),
            workflow_id=uuid.UUID(str(workflow_id)),
        )

        if not row:
            raise ValueError("Workflow not found")

        workflow = row.get("workflow") or {}

    if workflow is None:
        raise ValueError("workflow.run job requires workflow or workflow_id")

    thread_id = payload.get("thread_id") or str(uuid.uuid4())

    runtime_tools = payload.get("_runtime_tools") or build_tools()

    runtime_ctx = build_application_runtime_context(
        request=_dummy_request(tools=runtime_tools),
        user_id=uuid.UUID(str(user_id)),
        thread_id=uuid.UUID(str(thread_id)),
        db=ctx.db,
        extras={
            **(payload.get("extras") or {}),
            "_job": {
                "id": str(ctx.job.id),
                "attempt": ctx.job.attempts,
                "max_attempts": ctx.job.max_attempts,
            },
        },
        run_store=build_run_store(ctx.db),
        event_sink=build_event_sink(ctx.db),
    )

    result = await execute_workflow_dag(
        ctx=runtime_ctx,
        workflow=workflow,
        message=payload.get("message") or "",
        strict=payload.get("strict", True),
        resume_workflow_run_id=payload.get("resume_workflow_run_id"),
    )

    _raise_if_workflow_failed(result)

    return jsonable_encoder(result)


async def resume_workflow_job(
    payload: dict[str, Any],
    ctx: JobContext,
) -> dict[str, Any]:
    register_application_nodes()

    user_id = ctx.job.user_id or payload.get("user_id")

    if user_id is None:
        raise ValueError("workflow.resume job requires user_id")

    workflow_run_id = payload.get("workflow_run_id") or payload.get("run_id")
    resume_input = payload.get("input") or payload.get("resume_input") or {}

    if not workflow_run_id:
        raise ValueError("workflow.resume job requires workflow_run_id")

    runtime_tools = payload.get("_runtime_tools") or build_tools()

    runtime_ctx = build_application_runtime_context(
        request=_dummy_request(tools=runtime_tools),
        user_id=uuid.UUID(str(user_id)),
        thread_id=uuid.uuid4(),
        db=ctx.db,
        extras={
            "resume_input": payload.get("input") or {},
            **(payload.get("extras") or {}),
            "_job": {
                "id": str(ctx.job.id),
                "attempt": ctx.job.attempts,
                "max_attempts": ctx.job.max_attempts,
            },
        },
        run_store=build_run_store(ctx.db),
        event_sink=build_event_sink(ctx.db),
    )

    ctx.resume_input = resume_input

    result = await execute_workflow_dag(
        ctx=runtime_ctx,
        workflow={},
        message="",
        strict=payload.get("strict", False),
        resume_workflow_run_id=workflow_run_id,
    )

    _raise_if_workflow_failed(result)

    return jsonable_encoder(result)


def register_workflow_job_handlers(registry) -> None:
    registry.register("workflow.run", run_workflow_job)
    registry.register("workflow.resume", resume_workflow_job)
    registry.register("workflow.replay", replay_workflow_job)


async def replay_workflow_job(payload, ctx):
    from uuid import UUID

    from app.workflow_operations.snapshots.service import WorkflowSnapshotService

    class _State:
        tools = None

    class _Request:
        state = _State()

    snapshot_id = payload.get("snapshot_id")

    if not snapshot_id:
        raise ValueError("workflow.replay job requires snapshot_id")

    snapshot = await WorkflowSnapshotService(ctx.db).get_or_404(
        snapshot_id=UUID(str(snapshot_id)),
        user_id=ctx.job.user_id,
    )

    run_store = build_run_store(ctx.db)
    original_run = await run_store.load_run(
        run_id=snapshot.workflow_run_id,
    )

    if not original_run:
        raise ValueError("workflow.replay could not load original workflow run")

    replay_ctx = build_application_runtime_context(
        request=_Request(),
        user_id=ctx.job.user_id,
        thread_id=ctx.job.id,
        db=ctx.db,
        extras={
            "_job": {
                "id": str(ctx.job.id),
                "attempt": ctx.job.attempts,
                "max_attempts": ctx.job.max_attempts,
            },
        },
        run_store=run_store,
    )

    result = await execute_workflow_dag(
        ctx=replay_ctx,
        workflow=original_run["workflow"],
        message="",
        replay_state=snapshot.state,
        replay_parent_workflow_run_id=str(snapshot.workflow_run_id),
    )

    _raise_if_workflow_failed(result)

    return {
        "mode": "replay_execution",
        "snapshot": {
            "id": str(snapshot.id),
            "workflow_run_id": str(snapshot.workflow_run_id),
            "seq": snapshot.seq,
            "snapshot_type": snapshot.snapshot_type,
            "node_id": snapshot.node_id,
            "node_type": snapshot.node_type,
        },
        "replay_supported": True,
        "result": result,
    }
