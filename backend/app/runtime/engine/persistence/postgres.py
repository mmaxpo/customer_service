from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional, List
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def to_jsonb_str(obj: Any) -> str:
    """

    Convert Python objects into a JSON string suitable for Postgres JSONB.

    FastAPI's jsonable_encoder converts non-JSON-native values such as UUID,

    datetime, and Pydantic models into JSON-safe types.

    This is used with:

        CAST(:param AS jsonb)

    Args:

        obj: Any JSON-like Python object.

    Returns:

        str: JSON string.

    Example:

        payload = {"workflow_run_id": uuid.uuid4()}

        json_str = to_jsonb_str(payload)

        assert isinstance(json_str, str)

    """
    safe = jsonable_encoder(obj)
    return json.dumps(safe, ensure_ascii=False)


class PostgresRunStore:
    """
    Postgres-backed implementation of RunStore.

    Stores workflow run metadata and full RunState in workflow_runs.

    Responsibilities:
        - create workflow run rows
        - update run status/state/extra
        - load runs for resume
        - list runs for UI/history
        - list events for replay/SSE

    Example:
        store = PostgresRunStore(db)

        await store.create_run(
            run_id=run_id,
            user_id=user_id,
            thread_id=thread_id,
            workflow=workflow,
            state=state,
        )
    """

    def __init__(self, db: AsyncSession):
        """
        Store the SQLAlchemy async session.
        Args:
            db: AsyncSession for database operations.
        """
        self.db = db

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
        """
        Create a workflow run row.
        This is called once when a new workflow execution starts.

        Stored fields:
            workflow_run_id
            user_id
            thread_id
            status
            workflow
            state
            extra

        Uses ON CONFLICT DO NOTHING so duplicate create attempts do not crash.

        Example:
            await store.create_run(
                run_id=state["workflow_run_id"],
                user_id=ctx.user_id,
                thread_id=ctx.thread_id,
                workflow=workflow,
                state=state,
            )
        """

        q = text(
            """
            INSERT INTO workflow_runs (workflow_run_id, user_id, thread_id, status, workflow, state, extra)
            VALUES (
              :workflow_run_id, :user_id, :thread_id, :status,
              CAST(:workflow AS jsonb),
              CAST(:state AS jsonb),
              CAST(:extra AS jsonb)
            )
            ON CONFLICT (workflow_run_id) DO NOTHING
            """
        )

        params = {
            "workflow_run_id": run_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "status": status,
            "workflow": to_jsonb_str(workflow),
            "state": to_jsonb_str(state),
            "extra": to_jsonb_str(extra or {}),
        }

        await self.db.execute(q, params)
        await self.db.commit()

    async def update_run(
        self,
        *,
        run_id: uuid.UUID,
        status: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """

        Update a workflow run status, state, and/or extra metadata.

        Any value passed as None is ignored and the existing database value is kept.

        Common statuses:

            running

            paused

            done

            failed

            cancelled

        Example:

            await store.update_run(

                run_id=run_id,

                status="paused",

                state=state,

                extra={"interrupt": interrupt},

            )

        """
        q = text(
            """
            UPDATE workflow_runs
            SET
              status = COALESCE(:status, status),
              state  = COALESCE(CAST(:state AS jsonb), state),
              extra  = COALESCE(CAST(:extra AS jsonb), extra),
              updated_at = now()
            WHERE workflow_run_id = :workflow_run_id
            """
        )

        params = {
            "workflow_run_id": run_id,
            "status": status,
            "state": to_jsonb_str(state) if state is not None else None,
            "extra": to_jsonb_str(extra) if extra is not None else None,
        }

        await self.db.execute(q, params)
        await self.db.commit()

    async def claim_run_for_resume(
        self, *, run_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically claim a paused workflow run for resume.

        This prevents two workers/jobs from both loading the same paused run and
        executing downstream side-effect nodes twice.

        Returns the run row only when this call successfully transitions:

            paused -> running

        If the run is already running/done/failed/cancelled/missing, returns None.
        The caller can then load_run() to report the current status.
        """
        q = text(
            """
            UPDATE workflow_runs
            SET status = 'running',
                updated_at = now()
            WHERE workflow_run_id = :workflow_run_id
              AND status = 'paused'
            RETURNING workflow_run_id,
                      user_id,
                      thread_id,
                      status,
                      workflow,
                      state,
                      extra,
                      created_at,
                      updated_at
            """
        )

        res = await self.db.execute(q, {"workflow_run_id": run_id})
        row = res.mappings().first()
        await self.db.commit()

        return dict(row) if row else None

    async def load_run(self, *, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """

        Load a workflow run for resume or inspection.

        Used by execute_workflow_dag(..., resume_workflow_run_id=...) to recover:

            - saved workflow

            - saved state

            - current status

        Args:

            run_id: Workflow run UUID.

        Returns:

            dict | None:

                Run row as a dictionary, or None if not found.

        Example:

            saved = await store.load_run(run_id=run_id)

            if saved and saved["status"] == "paused":

                workflow = saved["workflow"]

                state = saved["state"]

        """
        q = text(
            """
            SELECT workflow_run_id, user_id, thread_id, status, workflow, state, extra, created_at, updated_at
            FROM workflow_runs
            WHERE workflow_run_id = :workflow_run_id
            """
        )
        res = await self.db.execute(q, {"workflow_run_id": run_id})
        row = res.mappings().first()
        return dict(row) if row else None

    # Back-compat alias if you still call get_run somewhere else
    async def get_run(self, *, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Backward-compatible alias for load_run().
        Example:
            run = await store.get_run(run_id=run_id)
        """
        return await self.load_run(run_id=run_id)

    async def get_run_public(self, *, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Load public run information without returning full workflow JSON.
        Useful for UI views where the client needs run status and state but not
        necessarily the full workflow definition.

        Example:
            run = await store.get_run_public(run_id=run_id)
            assert "status" in run
        """
        q = text(
            """
            SELECT workflow_run_id,
                   user_id,
                   thread_id,
                   status,
                   state,
                   extra,
                   created_at,
                   updated_at
            FROM workflow_runs
            WHERE workflow_run_id = :workflow_run_id
            """
        )
        res = await self.db.execute(q, {"workflow_run_id": run_id})
        row = res.mappings().first()
        return dict(row) if row else None

    async def get_last_pause_interrupt(
        self, *, run_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """

        Return the latest pause interrupt payload for a run.

        Lookup order:

            1. workflow_runs.extra["interrupt"]

            2. latest run_paused event in workflow_run_events

        This helps frontend restore the human approval/manual input state.

        Example:

            interrupt = await store.get_last_pause_interrupt(run_id=run_id)

            if interrupt:

                show_human_approval_ui(interrupt)

        """
        q1 = text(
            """
            SELECT extra
            FROM workflow_runs
            WHERE workflow_run_id = :workflow_run_id
            """
        )
        r1 = await self.db.execute(q1, {"workflow_run_id": run_id})
        row1 = r1.mappings().first()
        if row1 and row1.get("extra") and isinstance(row1["extra"], dict):
            intr = row1["extra"].get("interrupt")
            if intr:
                return intr

        # Fallback: last run_paused event
        q2 = text(
            """
            SELECT event
            FROM workflow_run_events
            WHERE workflow_run_id = :workflow_run_id
              AND event ->>'event' = 'run_paused'
            ORDER BY id DESC
                LIMIT 1
            """
        )
        r2 = await self.db.execute(q2, {"workflow_run_id": run_id})
        row2 = r2.mappings().first()
        if not row2:
            return None
        ev = row2["event"]
        if isinstance(ev, dict):
            return ev.get("interrupt")
        return None

    async def list_runs(
        self,
        *,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """

        List workflow runs for a user.

        Supports optional status filtering and pagination.

        Args:

            user_id: Owner user id.

            status: Optional run status filter.

            limit: Maximum rows to return.

            offset: Pagination offset.

        Returns:

            list[dict]: Run summaries ordered newest first.

        Example:

            runs = await store.list_runs(

                user_id=user_id,

                status="paused",

                limit=20,

            )

        """
        sql = """
              SELECT workflow_run_id,
                     status,
                     thread_id,
                     created_at,
                     updated_at,
                     extra,
                     state
              FROM workflow_runs
              WHERE user_id = :user_id \
              """
        params: Dict[str, Any] = {
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
        }

        if status:
            sql += " AND status = :status"
            params["status"] = status

        sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        res = await self.db.execute(text(sql), params)
        rows = res.mappings().all()
        return [dict(r) for r in rows]

    # TODO
    #  Small cleanup note
    #   get_run_state() and load_run() are almost identical. Later, keep one canonical method:
    #   load_run()
    async def get_run_state(self, *, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Load full persisted run state.
        This currently overlaps with load_run(). It can be kept for route-level
        naming clarity, but long-term you may merge it with load_run().
        Example:
            run_state = await store.get_run_state(run_id=run_id)
        """
        q = text(
            """
            SELECT workflow_run_id, user_id, thread_id, status, workflow, state, extra, created_at, updated_at
            FROM workflow_runs
            WHERE workflow_run_id = :workflow_run_id
            """
        )
        res = await self.db.execute(q, {"workflow_run_id": run_id})
        row = res.mappings().first()
        return dict(row) if row else None

    async def list_events(
        self,
        *,
        run_id: uuid.UUID,
        limit: int = 200,
        after_seq: int = 0,
    ) -> List[Dict[str, Any]]:
        """

        List workflow run events after a sequence id.

        Used for SSE replay/reconnect:

            - after_seq=0 returns all events

            - after_seq=N returns events with id > N

        Each returned row includes:

            id

            seq

            workflow_run_id

            event

            created_at

        Args:

            run_id: Workflow run UUID.

            limit: Maximum events to return.

            after_seq: Return events after this event id.

        Returns:

            list[dict]: Ordered event rows.

        Example:

            events = await store.list_events(

                run_id=run_id,

                after_seq=last_seen_seq,

            )

        """
        q = text(
            """
            SELECT id, workflow_run_id, event, created_at
            FROM workflow_run_events
            WHERE workflow_run_id = :workflow_run_id
              AND id > :after_seq
            ORDER BY id ASC LIMIT :limit
            """
        )
        res = await self.db.execute(
            q,
            {"workflow_run_id": run_id, "after_seq": after_seq, "limit": limit},
        )
        rows = res.mappings().all()

        out = []
        for r in rows:
            d = dict(r)
            d["seq"] = int(d["id"])
            # (optional) also attach seq inside event payload for frontend convenience
            if isinstance(d.get("event"), dict) and "seq" not in d["event"]:
                d["event"]["seq"] = d["seq"]
            out.append(d)
        return out


class PostgresEventSink:
    """

    Postgres-backed implementation of EventSink.

    Stores workflow runtime events in workflow_run_events.

    The inserted row id is also attached to the in-memory event as "seq",

    allowing the API response and SSE replay to share the same sequence id.

    """

    def __init__(self, db: AsyncSession):
        """
        Store the SQLAlchemy async session.
        Args:
            db: AsyncSession for database operations.
        """
        self.db = db

    async def emit(self, run_id: uuid.UUID, event: Dict[str, Any]) -> None:
        """
        Persist one runtime event.
        Inserts event into workflow_run_events and attaches the inserted row id
        back onto the in-memory event as event["seq"].
        Args:
            run_id: Workflow run UUID.
            event: Event payload emitted by the executor.
        Example:
            await sink.emit(
                run_id=run_id,
                event={"event": "node_start", "node_id": "kb"},
            )
            assert "seq" in event
        """
        q = text(
            """
            INSERT INTO workflow_run_events (workflow_run_id, event)
            VALUES (:workflow_run_id, CAST(:event AS jsonb))
            RETURNING id
            """
        )

        res = await self.db.execute(
            q,
            {"workflow_run_id": run_id, "event": to_jsonb_str(event)},
        )

        seq = res.scalar_one()  # the inserted row id
        # attach seq to the in-memory event too (so executor return meta has it)
        event["seq"] = int(seq)

        await self.db.commit()
