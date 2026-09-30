from __future__ import annotations

import copy
import uuid
from typing import Any, Dict, Optional

from app.runtime.engine.persistence.types import RunStore, EventSink


class InMemoryRunStore(RunStore):
    def __init__(self):
        self.runs: Dict[uuid.UUID, Dict[str, Any]] = {}

    async def create_run(
        self,
        *,
        run_id: uuid.UUID,
        user_id,
        thread_id,
        workflow: Dict[str, Any],
        state: Dict[str, Any],
        status: str = "running",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.runs.setdefault(
            run_id,
            {
                "workflow_run_id": run_id,
                "user_id": user_id,
                "thread_id": thread_id,
                "status": status,
                "workflow": copy.deepcopy(workflow),
                "state": copy.deepcopy(state),
                "extra": copy.deepcopy(extra or {}),
            },
        )

    async def update_run(
        self,
        *,
        run_id: uuid.UUID,
        status: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        r = self.runs.get(run_id)
        if not r:
            return
        if status is not None:
            r["status"] = status
        if state is not None:
            r["state"] = copy.deepcopy(state)
        if extra is not None:
            r["extra"] = copy.deepcopy(extra)

    async def load_run(self, *, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        r = self.runs.get(run_id)
        return copy.deepcopy(r) if r else None


class InMemoryEventSink(EventSink):
    def __init__(self):
        self.events: list[dict] = []

    async def emit(self, run_id: uuid.UUID, event: Dict[str, Any]) -> None:
        self.events.append({"workflow_run_id": str(run_id), **event})
