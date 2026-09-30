import asyncio
import uuid
from datetime import datetime, timezone
import pytest
import httpx

from app.main import app
from app.api.auth import get_current_user
from app.api.workflows import get_run_store, get_event_sink


class FakeUser:
    def __init__(self, user_id: uuid.UUID):
        self.id = user_id


class TinyInMemoryRunStore:
    """
    Minimal in-memory run store for:
      - /workflows_route/run (executor calls create_run/update_run)
      - /workflows_route/runs/{id}/stream (calls get_run_public + list_events)
    """

    def __init__(self):
        self.runs: dict[uuid.UUID, dict] = {}
        self.events_by_run: dict[uuid.UUID, list[dict]] = {}
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def create_run(
        self,
        *,
        run_id: uuid.UUID,
        user_id: uuid.UUID | None,
        thread_id: uuid.UUID | None,
        workflow: dict,
        state: dict,
        status: str = "running",
        extra: dict | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.runs[run_id] = {
            "workflow_run_id": run_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "status": status,
            "workflow": workflow,
            "state": state,
            "extra": extra or {},
            "created_at": now,
            "updated_at": now,
        }
        self.events_by_run.setdefault(run_id, [])

    async def update_run(
        self,
        *,
        run_id: uuid.UUID,
        status: str | None = None,
        state: dict | None = None,
        extra: dict | None = None,
    ) -> None:
        row = self.runs.get(run_id)
        if not row:
            return
        if status is not None:
            row["status"] = status
        if state is not None:
            row["state"] = state
        if extra is not None:
            row["extra"] = extra
        row["updated_at"] = datetime.now(timezone.utc)

    async def get_run_public(self, *, run_id: uuid.UUID):
        row = self.runs.get(run_id)
        if not row:
            return None
        return {
            "workflow_run_id": row["workflow_run_id"],
            "user_id": row["user_id"],
            "thread_id": row["thread_id"],
            "status": row["status"],
            "state": row["state"],
            "extra": row["extra"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def list_events(
        self, *, run_id: uuid.UUID, limit: int = 200, after_seq: int = 0
    ):
        evs = self.events_by_run.get(run_id, [])
        out = []
        for e in evs:
            seq = int(e["id"])
            if seq > after_seq:
                d = dict(e)
                d["seq"] = seq
                out.append(d)
            if len(out) >= limit:
                break
        return out

    async def _append_event(self, run_id: uuid.UUID, event: dict) -> int:
        now = datetime.now(timezone.utc)
        seq = self._next_seq()
        self.events_by_run.setdefault(run_id, []).append(
            {
                "id": seq,
                "workflow_run_id": run_id,
                "event": event,
                "created_at": now,
            }
        )
        return seq


class TinyInMemoryEventSink:
    def __init__(self, store: TinyInMemoryRunStore):
        self.store = store

    async def emit(self, run_id: uuid.UUID, event: dict) -> None:
        seq = await self.store._append_event(run_id, event)
        event["seq"] = int(seq)


async def read_n_event_ids(stream, n: int) -> list[int]:
    """
    Read N SSE `id:` values from the stream and return them.
    Stops early as soon as it has N.
    """
    ids: list[int] = []
    async for line in stream.aiter_lines():
        if line.startswith("id:"):
            ids.append(int(line.split(":", 1)[1].strip()))
            if len(ids) >= n:
                return ids
    return ids


@pytest.mark.asyncio
async def test_sse_stream_reconnect_no_replay_ids():
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    mem_store = TinyInMemoryRunStore()
    mem_sink = TinyInMemoryEventSink(mem_store)

    app.dependency_overrides[get_run_store] = lambda: mem_store
    app.dependency_overrides[get_event_sink] = lambda: mem_sink

    wf = {
        "nodes": [
            {"id": "t1", "data": {"nodeType": "trigger.message", "input": "start"}},
            {"id": "r1", "data": {"nodeType": "response"}},
        ],
        "edges": [{"id": "e1", "source": "t1", "target": "r1"}],
    }

    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Start run
            r = await client.post(
                "/workflows_route/run", json={"workflow": wf, "message": ""}
            )
            assert r.status_code == 200
            run_id = r.json()["meta"]["workflow_run_id"]

            url = f"/workflows_route/runs/{run_id}/stream?after_seq=0"

            # Read first few event ids (don’t drain forever)
            async with client.stream("GET", url) as s1:
                ids1 = await asyncio.wait_for(read_n_event_ids(s1, n=3), timeout=2.0)

            assert len(ids1) >= 1, "No SSE ids received"
            last_seen = ids1[-1]

            # Reconnect with Last-Event-ID and ensure we only see ids > last_seen
            async with client.stream(
                "GET", url, headers={"Last-Event-ID": str(last_seen)}
            ) as s2:
                ids2 = await asyncio.wait_for(read_n_event_ids(s2, n=2), timeout=2.0)

            # If run already ended, ids2 may be empty (stream-open/heartbeat only).
            # But if we get any ids, they must be strictly greater than last_seen.
            for x in ids2:
                assert x > last_seen, f"Replayed event id {x} (last_seen={last_seen})"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_run_store, None)
        app.dependency_overrides.pop(get_event_sink, None)
