from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional, List


class InMemoryRunStore:
    def __init__(self):
        # run_id -> row
        self._runs: dict[uuid.UUID, dict] = {}
        # run_id -> list of events rows {id, seq, event, created_at}
        self._events: dict[uuid.UUID, list[dict]] = {}
        self._seq = 0

    async def create_run(
        self,
        *,
        run_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        thread_id: Optional[uuid.UUID],
        workflow: Dict[str, Any],
        state: Dict[str, Any],
        status: str = "running",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._runs.setdefault(
            run_id,
            {
                "workflow_run_id": run_id,
                "user_id": user_id,
                "thread_id": thread_id,
                "status": status,
                "workflow": workflow,
                "state": state,
                "extra": extra or {},
                "created_at": time.time(),
                "updated_at": time.time(),
            },
        )
        self._events.setdefault(run_id, [])

    async def update_run(
        self,
        *,
        run_id: uuid.UUID,
        status: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        row = self._runs.get(run_id)
        if not row:
            return
        if status is not None:
            row["status"] = status
        if state is not None:
            row["state"] = state
        if extra is not None:
            row["extra"] = extra
        row["updated_at"] = time.time()

    async def load_run(self, *, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        return self._runs.get(run_id)

    async def get_run_public(self, *, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        return self._runs.get(run_id)

    async def list_events(
        self, *, run_id: uuid.UUID, limit: int = 200, after_seq: int = 0
    ) -> List[Dict[str, Any]]:
        rows = self._events.get(run_id, [])
        out = []
        for r in rows:
            if int(r["seq"]) > int(after_seq):
                out.append(r)
            if len(out) >= limit:
                break
        return out


class InMemoryEventSink:
    def __init__(self, store: InMemoryRunStore):
        self.store = store

    async def emit(self, run_id: uuid.UUID, event: Dict[str, Any]) -> None:
        self.store._seq += 1
        seq = self.store._seq
        event["seq"] = seq
        row = {
            "id": seq,
            "seq": seq,
            "workflow_run_id": run_id,
            "event": event,
            "created_at": time.time(),
        }
        self.store._events.setdefault(run_id, []).append(row)
