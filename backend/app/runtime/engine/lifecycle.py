from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


EmitFn = Callable[[dict[str, Any]], Awaitable[None]]
SnapshotFn = Callable[..., Awaitable[None]]


async def initialize_run_lifecycle(
    *,
    run_store: Any,
    ctx: Any,
    workflow: dict[str, Any],
    state: dict[str, Any],
    is_resume: bool,
    emit: EmitFn,
    capture_snapshot: SnapshotFn,
) -> None:
    """Initialize persistent run row and emit start/resume lifecycle events."""

    if run_store and not is_resume:
        await run_store.create_run(
            run_id=state["workflow_run_id"],
            user_id=getattr(ctx, "user_id", None),
            thread_id=getattr(ctx, "thread_id", None),
            workflow=workflow,
            state=state,
        )

    if is_resume:
        resume_event = {
            "event": "run_resume",
            "workflow_run_id": str(state["workflow_run_id"]),
        }
        await emit(resume_event)
        await capture_snapshot("run_resume", event=resume_event)
        return

    start_event = {
        "event": "run_start",
        "workflow_run_id": str(state["workflow_run_id"]),
    }
    await emit(start_event)
    await capture_snapshot("run_start", event=start_event)
