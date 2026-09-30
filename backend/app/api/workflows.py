from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.core.session import get_db as get_session
from app.runtime.execution import execute_workflow_dag
from app.runtime.nodes.registry import list_registered_nodes
from app.runtime.persistence import build_event_sink, build_run_store
from app.runtime.validation import validate_workflow
from app.runtime.workflows import build_runtime_workflow_repository
from app.runtime_services import build_application_runtime_context
from app.workflow_operations.waits.service import WorkflowWaitService

# ============================================================
# HTTP transport schemas
# ============================================================


class RunReq(BaseModel):
    workflow: dict
    message: str = ""
    thread_id: str | None = None
    resume_workflow_run_id: str | None = None
    strict: bool = True  # ✅ optional but useful


class ResumeReq(BaseModel):
    workflow_run_id: str
    input: dict | None = None  # optional human payload
    strict: bool = True


class RunDetailsOut(BaseModel):
    workflow_run_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    thread_id: Optional[str] = None
    answer: Optional[str] = None
    interrupt: Optional[dict] = None


class RunEventsOut(BaseModel):
    workflow_run_id: str
    events: List[dict]


class RunsListOut(BaseModel):
    items: List[RunDetailsOut]
    limit: int
    offset: int
    status: Optional[str] = None


class WorkflowCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    workflow: dict


class WorkflowUpdateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    workflow: dict


class RunByIdReq(BaseModel):
    message: str = ""
    thread_id: str | None = None
    resume_workflow_run_id: str | None = None
    strict: bool = True


# ============================================================
# HTTP dependencies
# ============================================================


def get_run_store(request: Request, db=Depends(get_session)):
    return getattr(request.state, "run_store", None) or build_run_store(db)


def get_event_sink(request: Request, db=Depends(get_session)):
    return getattr(request.state, "event_sink", None) or build_event_sink(db)


# ============================================================
# Workflow API
# ============================================================

router = APIRouter(prefix="/workflows_route", tags=["workflows_route"])


# ------------------------------------------------------------
# Run event stream
# ------------------------------------------------------------


def _iso_created_at(v):
    if v is None:
        return None
    # datetime -> iso
    if isinstance(v, datetime):
        return v.isoformat()
    # float/int (unix seconds) -> iso
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
    # already string
    return str(v)


def _as_event_dict(ev):
    # ev might be dict, JSON string, or something else
    if isinstance(ev, dict):
        return ev
    if isinstance(ev, str):
        try:
            parsed = json.loads(ev)
            return parsed if isinstance(parsed, dict) else {"raw": ev}
        except Exception:
            return {"raw": ev}
    return {"raw": ev}


@router.get("/runs/{workflow_run_id}/stream")
async def stream_run_events(
    workflow_run_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    run_store=Depends(get_run_store),
    after_seq: int = Query(default=0, ge=0),
    heartbeat_sec: int = Query(default=15, ge=5, le=60),
):
    store = run_store
    rid = UUID(workflow_run_id)

    row = await store.get_run_public(run_id=rid)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    if row.get("user_id") and row["user_id"] != UUID(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Forbidden")

    last_event_id = request.headers.get("last-event-id") or request.headers.get(
        "Last-Event-ID"
    )
    header_after = (
        int(last_event_id) if (last_event_id and str(last_event_id).isdigit()) else 0
    )
    after_seq = max(int(after_seq or 0), header_after)

    async def event_gen():
        last = after_seq
        last_beat = time.time()

        # if run already terminal, we still want to flush remaining events then close
        terminal_status = row.get("status") in ("done", "failed", "cancelled")

        yield ": stream-open\n\n"

        try:
            while True:
                # in ASGITransport, this may be unreliable, but keep it anyway
                if await request.is_disconnected():
                    return

                batch = await store.list_events(run_id=rid, limit=200, after_seq=last)

                if batch:
                    for r in batch:
                        seq = int(r.get("seq") or r.get("id") or 0)
                        if seq <= last:
                            continue
                        last = seq

                        ev = _as_event_dict(r.get("event"))
                        payload = {
                            "seq": seq,
                            "event": ev,
                            "created_at": _iso_created_at(r.get("created_at")),
                        }

                        yield f"id: {seq}\n"
                        yield "event: run_event\n"
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                        if ev.get("event") in (
                            "run_end",
                            "run_failed",
                            "run_cancelled",
                        ):
                            return

                # ✅ important: if run is already terminal and there are no new events, close
                if terminal_status and not batch:
                    return

                now = time.time()
                if now - last_beat >= heartbeat_sec:
                    last_beat = now
                    hb = {"ts": int(now), "seq": last}
                    yield f"event: heartbeat\ndata: {json.dumps(hb)}\n\n"

                await asyncio.sleep(0.2)

        except asyncio.CancelledError:
            # ✅ this is the big one: client closed stream => server task cancelled
            return

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ------------------------------------------------------------
# Workflow runs
# ------------------------------------------------------------


@router.post("/run")
async def run_workflow(
    req: RunReq,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
    run_store=Depends(get_run_store),
    event_sink=Depends(get_event_sink),
):
    # If frontend gives thread_id → use it
    # If not → create a new conversation id
    thread_id = req.thread_id or str(uuid.uuid4())
    # Important:
    # thread_id = conversation identity
    # workflow_run_id = workflow execution identity
    # Example:
    # Customer conversation: thread_id = A
    # First workflow run:    run_id = 1
    # Human approval resume: run_id = 1 again
    # Another message:       run_id = 2
    """
    RuntimeContext is the backpack passed through the whole workflow.
    Every node can access it.
    Simple meaning: RuntimeContext = everything a node needs from the outside world
    """
    ctx = build_application_runtime_context(
        request=request,
        user_id=UUID(str(current_user.id)),
        thread_id=UUID(thread_id),
        db=db,
        extras={},
        run_store=run_store,
        event_sink=event_sink,
    )
    """
    This is where the real execution starts.
    Its job:    Run a workflow graph safely, node by node.
    Meaning:
    Take this workflow JSON
    Take this user message
    Use this context

    Run the graph
    Return final answer + metadata
    --------------
    It supports:
    new run
    resume paused run
    validation
    state
    events
    parallel execution
    routing
    skipping
    pause/resume
    loop
    errors
    final response
    -------------------
    Step 1 — get persistence objects
    run_store = getattr(ctx, "run_store", None) -> Can I save workflow state?
    event_sink = getattr(ctx, "event_sink", None) -> Can I save workflow events?
    """

    return await execute_workflow_dag(
        ctx=ctx,
        workflow=req.workflow,
        message=req.message,
        strict=req.strict,
        resume_workflow_run_id=req.resume_workflow_run_id,
    )


@router.post("/resume")
async def resume_workflow(
    req: ResumeReq,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
    run_store=Depends(get_run_store),
    event_sink=Depends(get_event_sink),
):
    rid = UUID(req.workflow_run_id)

    row = await run_store.get_run_public(
        run_id=rid,
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    if row.get("user_id") != UUID(str(current_user.id)):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

    # Keep thread_id from DB (executor will load it from state),
    # but ctx.thread_id still must exist for nodes that use it.
    # We'll set a dummy for now and let executor override state.
    dummy_thread_id = uuid.uuid4()

    ctx = build_application_runtime_context(
        request=request,
        user_id=UUID(str(current_user.id)),
        thread_id=dummy_thread_id,
        db=db,
        extras={},
        run_store=run_store,
        event_sink=event_sink,
    )

    # If user provided human input, merge it into state.vars on resume.
    # We'll pass it via ctx.extras so executor can apply it.
    if req.input:
        ctx.extras["resume_input"] = req.input

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow={},  # ignored in resume mode (loaded from DB)
        message="",
        strict=req.strict,
        resume_workflow_run_id=req.workflow_run_id,
    )

    meta = result.get("meta") or {}
    status = meta.get("status")
    current_status = meta.get("current_status")

    # A synchronous successful resume must close its durable wait.
    #
    # Also reconcile a historical stale wait when a duplicate request finds
    # that the workflow run already reached its terminal done state.
    if status == "ok" or (
        meta.get("error") == "run_not_paused" and current_status == "done"
    ):
        await WorkflowWaitService(db).resolve_waits_for_completed_run(
            user_id=current_user.id,
            workflow_run_id=req.workflow_run_id,
            resolution=req.input or {},
        )

    return result


@router.get("/runs")
async def list_runs(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_session),
    current_user=Depends(get_current_user),
    run_store=Depends(get_run_store),
):
    store = run_store
    rows = await store.list_runs(
        user_id=UUID(str(current_user.id)),
        status=status,
        limit=limit,
        offset=offset,
    )

    # return a compact list for UI
    out = []
    for r in rows:
        st = r.get("state") or {}
        extra = r.get("extra") or {}

        rid = r["workflow_run_id"]

        # ✅ Always correct interrupt source
        interrupt = None
        if r["status"] == "paused":
            interrupt = await store.get_last_pause_interrupt(run_id=rid)
        else:
            interrupt = extra.get("interrupt") if isinstance(extra, dict) else None

        out.append(
            {
                "workflow_run_id": str(r["workflow_run_id"]),
                "status": r["status"],
                "thread_id": str(r["thread_id"]) if r.get("thread_id") else None,
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "answer": (st.get("last") if isinstance(st, dict) else None),
                "interrupt": interrupt,
            }
        )

    return {"items": out, "limit": limit, "offset": offset, "status": status}


@router.get("/runs/{workflow_run_id}", response_model=RunDetailsOut)
async def get_run_details(
    workflow_run_id: str,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    store = build_run_store(db)
    rid = UUID(workflow_run_id)

    row = await store.get_run_public(run_id=rid)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    # ✅ ownership check
    if row.get("user_id") and row["user_id"] != UUID(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Forbidden")

    state = row.get("state") if isinstance(row.get("state"), dict) else {}

    answer = None
    if isinstance(state, dict):
        vars_ = state.get("vars") if isinstance(state.get("vars"), dict) else {}
        answer = vars_.get("answer") or state.get("last")

    interrupt = None
    if row["status"] == "paused":
        interrupt = await store.get_last_pause_interrupt(run_id=rid)

    return RunDetailsOut(
        workflow_run_id=str(row["workflow_run_id"]),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        thread_id=str(row["thread_id"]) if row.get("thread_id") else None,
        answer=answer,
        interrupt=interrupt,
    )


@router.get("/runs/{workflow_run_id}/state")
async def get_run_state(
    workflow_run_id: str,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    store = build_run_store(db)
    rid = UUID(workflow_run_id)

    row = await store.get_run_state(run_id=rid)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    # ownership
    if row.get("user_id") and row["user_id"] != UUID(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Forbidden")

    # return full payload (workflow + state) for UI rehydrate
    return {
        "workflow_run_id": str(row["workflow_run_id"]),
        "status": row["status"],
        "thread_id": str(row["thread_id"]) if row.get("thread_id") else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "workflow": row.get("workflow") or {},
        "state": row.get("state") or {},
        "extra": row.get("extra") or {},
    }


@router.get("/runs/{workflow_run_id}/events", response_model=RunEventsOut)
async def get_run_events(
    workflow_run_id: str,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
    limit: int = Query(default=200, ge=1, le=1000),
    after_seq: int = Query(default=0, ge=0),
):
    store = build_run_store(db)
    rid = UUID(workflow_run_id)

    row = await store.get_run_public(run_id=rid)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    if row.get("user_id") and row["user_id"] != UUID(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Forbidden")

    events = await store.list_events(run_id=rid, limit=limit, after_seq=after_seq)

    # stringify uuid for response
    for e in events:
        if "workflow_run_id" in e and e["workflow_run_id"] is not None:
            e["workflow_run_id"] = str(e["workflow_run_id"])

    return {"workflow_run_id": workflow_run_id, "events": events}


# ------------------------------------------------------------
# Workflow definitions
# ------------------------------------------------------------


@router.post("/runtime")
async def create_runtime_workflow(
    payload: WorkflowCreateIn,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    repo = build_runtime_workflow_repository(db)
    row = await repo.create(
        user_id=UUID(str(current_user.id)), name=payload.name, workflow=payload.workflow
    )
    return {"id": str(row["id"]), "name": payload.name}


@router.get("/runtime")
async def list_runtime_workflows(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    repo = build_runtime_workflow_repository(db)
    rows = await repo.list(
        user_id=UUID(str(current_user.id)), limit=limit, offset=offset
    )
    # stringify UUIDs
    for r in rows:
        r["id"] = str(r["id"])
    return {"items": rows, "limit": limit, "offset": offset}


@router.get("/runtime/{workflow_id}")
async def get_runtime_workflow(
    workflow_id: str,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    repo = build_runtime_workflow_repository(db)
    row = await repo.get(
        user_id=UUID(str(current_user.id)), workflow_id=UUID(workflow_id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    row["id"] = str(row["id"])
    row["user_id"] = str(row["user_id"])
    return row


@router.put("/runtime/{workflow_id}")
async def update_runtime_workflow(
    workflow_id: str,
    payload: WorkflowUpdateIn,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    repo = build_runtime_workflow_repository(db)
    ok = await repo.update(
        user_id=UUID(str(current_user.id)),
        workflow_id=UUID(workflow_id),
        name=payload.name,
        workflow=payload.workflow,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "ok"}


@router.delete("/runtime/{workflow_id}")
async def delete_runtime_workflow(
    workflow_id: str,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    repo = build_runtime_workflow_repository(db)
    ok = await repo.delete(
        user_id=UUID(str(current_user.id)), workflow_id=UUID(workflow_id)
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "ok"}


@router.post("/runtime/{workflow_id}/validate")
async def validate_runtime_workflow(
    workflow_id: str,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    repo = build_runtime_workflow_repository(db)
    row = await repo.get(
        user_id=UUID(str(current_user.id)), workflow_id=UUID(workflow_id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf = row.get("workflow") or {}
    errs = validate_workflow(wf, strict=True)
    return {"ok": len(errs) == 0, "errors": [e.to_dict() for e in errs]}


@router.post("/runtime/{workflow_id}/run")
async def run_runtime_workflow_by_id(
    workflow_id: str,
    payload: RunByIdReq,
    request: Request,
    db=Depends(get_session),
    current_user=Depends(get_current_user),
):
    repo = build_runtime_workflow_repository(db)
    row = await repo.get(
        user_id=UUID(str(current_user.id)), workflow_id=UUID(workflow_id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = row.get("workflow") or {}
    thread_id = payload.thread_id or str(uuid.uuid4())

    ctx = build_application_runtime_context(
        request=request,
        user_id=UUID(str(current_user.id)),
        thread_id=UUID(thread_id),
        db=db,
        extras={},
        run_store=build_run_store(db),
        event_sink=build_event_sink(db),
    )

    return await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message=payload.message,
        strict=payload.strict,
        resume_workflow_run_id=payload.resume_workflow_run_id,
    )


# ------------------------------------------------------------
# Runtime node catalog
# ------------------------------------------------------------


@router.get("/catalog/nodes")
async def get_node_catalog():
    return {"items": list_registered_nodes()}


__all__ = [
    "router",
    "get_run_store",
    "get_event_sink",
]
