from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.runtime.state.run_state import finish_run_state
from app.runtime.engine.responses import (
    build_paused_response,
    build_success_response,
)


EmitFn = Callable[[dict[str, Any]], Awaitable[None]]
PersistFn = Callable[[str, dict[str, Any] | None], Awaitable[None]]
SnapshotFn = Callable[..., Awaitable[None]]


async def pause_workflow_run(
    *,
    state: dict[str, Any],
    node_result: dict[str, Any],
    emit: EmitFn,
    persist: PersistFn,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist and return a paused workflow response."""
    interrupt = node_result.get("interrupt") or {}

    state["status"] = "paused"
    state.setdefault("meta", {})
    state["meta"]["interrupt"] = interrupt

    finish_run_state(state, "paused")

    await emit(
        {
            "event": "run_paused",
            "workflow_run_id": str(state["workflow_run_id"]),
            "interrupt": interrupt,
        }
    )

    await persist("paused", {"interrupt": interrupt})

    return build_paused_response(
        state=state,
        interrupt=interrupt,
        events=events,
    )


async def complete_workflow_run(
    *,
    state: dict[str, Any],
    steps: int,
    elapsed_sec: float,
    emit: EmitFn,
    persist: PersistFn,
    capture_snapshot: SnapshotFn,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist and return a successfully completed workflow response."""
    state.setdefault("meta", {})
    state["meta"]["interrupt"] = None

    finish_run_state(state, "done")

    await emit(
        {
            "event": "run_end",
            "workflow_run_id": str(state["workflow_run_id"]),
            "elapsed_sec": elapsed_sec,
        }
    )

    await persist("done", {"elapsed_sec": elapsed_sec, "steps": steps})

    await capture_snapshot(
        "run_completed",
        event={
            "answer": state.get("last"),
            "steps": steps,
            "elapsed_sec": elapsed_sec,
        },
    )

    return build_success_response(
        state=state,
        steps=steps,
        elapsed_sec=elapsed_sec,
        events=events,
    )
