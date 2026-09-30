from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable
import uuid


@runtime_checkable
class EventSink(Protocol):
    """
    Protocol for saving workflow runtime events.
    The executor emits events like:
        - run_start
        - node_start
        - node_end
        - node_error
        - run_paused
        - run_end

    Implementations can save these events to Postgres, memory, logs, or SSE systems.

    Example:
        await event_sink.emit(
            run_id=state["workflow_run_id"],
            event={"event": "node_start", "node_id": "kb"},
        )
    """

    async def emit(self, run_id: uuid.UUID, event: Dict[str, Any]) -> None: ...


@runtime_checkable
class RunStore(Protocol):
    """
    Protocol for persisting workflow run state.

    The executor uses RunStore to:
        - create a run record
        - update status/state
        - load paused runs for resume

    Implementations may use Postgres, Redis, in-memory storage, or another backend.

    Example:
        await run_store.create_run(
            run_id=state["workflow_run_id"],
            user_id=ctx.user_id,
            thread_id=ctx.thread_id,
            workflow=workflow,
            state=state,
        )
    """

    async def create_run(
        self,
        *,
        run_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        thread_id: Optional[uuid.UUID],
        workflow: Dict[str, Any],
        state: Dict[str, Any],
    ) -> None: ...

    async def update_run(
        self,
        *,
        run_id: uuid.UUID,
        status: str,
        state: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    async def load_run(self, *, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Load a workflow run by id.

        Returns:
            dict | None:
                {
                    "workflow_run_id": UUID,
                    "status": str,
                    "workflow": dict,
                    "state": dict,
                    "extra": dict,
                    ...
                }

        Example:
            saved = await run_store.load_run(run_id=run_id)

            if saved and saved["status"] == "paused":
                state = saved["state"]
        """

    ...
