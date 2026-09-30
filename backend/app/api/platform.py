from __future__ import annotations
import asyncio

# ============================================================
# app/jobs/router.py
# ============================================================
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.session import get_db
from app.core.session import SessionLocal
from app.platform.jobs.dead_letter import DeadLetterRepository
from app.platform.jobs.dead_letter_schemas import DeadLetterRead
from app.platform.jobs.metrics import JobMetricsService
from app.platform.jobs.recovery import JobRecoveryService
from app.platform.jobs.replay import JobReplayService
from app.platform.jobs.schemas import JobCreate, JobRead
from app.platform.jobs.service import JobService

jobs_router = APIRouter(
    prefix="/jobs",
    tags=["Platform Jobs"],
)


@jobs_router.post(
    "",
    response_model=JobRead,
)
async def enqueue_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await JobService(db).enqueue(
        user_id=current_user.id,
        job_type=payload.job_type,
        payload=payload.payload,
        max_attempts=payload.max_attempts,
        run_after=payload.run_after,
    )


@jobs_router.get(
    "",
    response_model=list[JobRead],
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await JobService(db).list_for_user(
        user_id=current_user.id,
    )


@jobs_router.get(
    "/dead-letters",
    response_model=list[DeadLetterRead],
)
async def list_dead_letters(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await DeadLetterRepository(db).list_for_user(
        user_id=current_user.id,
    )


@jobs_router.post(
    "/dead-letters/{dead_letter_id}/replay",
    response_model=JobRead,
)
async def replay_dead_letter(
    dead_letter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await JobReplayService(db).replay_dead_letter(
        user_id=current_user.id,
        dead_letter_id=dead_letter_id,
    )


@jobs_router.get("/metrics")
async def job_metrics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    metrics = JobMetricsService(db)

    return {
        "queue_depth": await metrics.queue_depth(
            user_id=current_user.id,
        ),
        "counts_by_status": await metrics.counts_by_status(
            user_id=current_user.id,
        ),
        "counts_by_type": await metrics.counts_by_type(
            user_id=current_user.id,
        ),
    }


@jobs_router.post("/recover")
async def recover_jobs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    jobs = await JobRecoveryService(db).recover_abandoned(
        user_id=current_user.id,
    )

    return {
        "recovered": len(jobs),
        "job_ids": [str(job.id) for job in jobs],
    }


@jobs_router.get(
    "/{job_id}",
    response_model=JobRead,
)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await JobService(db).get(
        job_id=job_id,
        user_id=current_user.id,
    )


# ============================================================
# app/schedules/router.py
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.session import get_db
from app.platform.schedules.scheduler import WorkflowScheduler
from app.platform.schedules.schemas import WorkflowScheduleCreate, WorkflowScheduleRead
from app.platform.schedules.service import WorkflowScheduleService

schedules_router = APIRouter(
    prefix="/schedules",
    tags=["Workflow Schedules"],
)


@schedules_router.post("", response_model=WorkflowScheduleRead)
async def create_schedule(
    payload: WorkflowScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowScheduleService(db).create(
        user_id=current_user.id,
        payload=payload,
    )


@schedules_router.get("", response_model=list[WorkflowScheduleRead])
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowScheduleService(db).list_for_user(
        user_id=current_user.id,
    )


@schedules_router.post("/{schedule_id}/pause", response_model=WorkflowScheduleRead)
async def pause_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowScheduleService(db).pause(
        user_id=current_user.id,
        schedule_id=schedule_id,
    )


@schedules_router.post("/{schedule_id}/resume", response_model=WorkflowScheduleRead)
async def resume_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowScheduleService(db).resume(
        user_id=current_user.id,
        schedule_id=schedule_id,
    )


@schedules_router.post("/tick")
async def tick_schedules(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowScheduler(db).tick(
        user_id=current_user.id,
    )


# ============================================================
# app/webhooks/router.py
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.session import get_db
from app.platform.webhooks.schemas import (
    WebhookDeliveryRead,
    WebhookEndpointCreate,
    WebhookEndpointRead,
)
from app.platform.webhooks.service import WebhookService

webhooks_router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)


@webhooks_router.post("/endpoints", response_model=WebhookEndpointRead)
async def create_endpoint(
    payload: WebhookEndpointCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WebhookService(db).create_endpoint(
        user_id=current_user.id,
        payload=payload,
    )


@webhooks_router.get("/endpoints", response_model=list[WebhookEndpointRead])
async def list_endpoints(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WebhookService(db).list_endpoints(
        user_id=current_user.id,
    )


@webhooks_router.post(
    "/{endpoint_id}/{event_type:path}", response_model=WebhookDeliveryRead
)
async def receive_webhook(
    endpoint_id: UUID,
    event_type: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    payload = await request.json()
    headers = dict(request.headers)

    return await WebhookService(db).receive(
        endpoint_id=endpoint_id,
        event_type=event_type,
        payload=payload,
        headers=headers,
        raw_body=raw_body,
    )


# ============================================================
# app/platform/events/router.py
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.session import get_db
from app.platform.events.event_store import PlatformEventStore
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.events.schemas import PlatformEventCreate, PlatformEventRead

events_router = APIRouter(
    prefix="/events",
    tags=["Platform Events"],
)


@events_router.post("", response_model=PlatformEventRead)
async def publish_event(
    payload: PlatformEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await PlatformEventPublisher(db).publish(
        user_id=current_user.id,
        event_type=payload.event_type,
        source=payload.source,
        payload=payload.payload,
        meta=payload.meta,
        dispatch=False,
    )

    return result["event"]


@events_router.get("", response_model=list[PlatformEventRead])
async def list_events(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await PlatformEventStore(db).list_for_user(
        user_id=current_user.id,
    )


@events_router.get("/{event_id}", response_model=PlatformEventRead)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    event = await PlatformEventStore(db).get(event_id)

    if event is None or event.user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    return event


# ============================================================
# app/realtime/router.py
# ============================================================

import asyncio
from contextlib import suppress
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.api.auth import get_current_user
from app.core.session import get_db
from app.tenancy.context import PrincipalResolver
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.realtime.codec import encode_sse_event, encode_sse_heartbeat
from app.platform.realtime.hub import realtime_hub
from app.platform.realtime.presence import PresenceLease

realtime_router = APIRouter(prefix="/realtime", tags=["Realtime"])


@realtime_router.get("/stream")
async def stream_realtime_events(
    request: Request,
    scope: str | None = Query(default=None),
    heartbeat_sec: int = Query(default=25, ge=5, le=60),
    workspace_id: UUID | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stream_owner_id = current_user.id
    if scope == "customer_service":
        principal = await PrincipalResolver(db).resolve(
            user=current_user,
            requested_workspace_id=workspace_id,
        )
        stream_owner_id = principal.workspace_id
    connection = await realtime_hub.register(
        user_id=stream_owner_id,
        scope=scope,
    )

    async def generator():
        yield ": stream-open\\n\\n"

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(
                        connection.queue.get(),
                        timeout=heartbeat_sec,
                    )
                except asyncio.TimeoutError:
                    yield encode_sse_heartbeat()
                    continue

                if event is None:
                    break

                yield encode_sse_event(event)
        finally:
            with suppress(Exception):
                await realtime_hub.unregister(connection)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@realtime_router.websocket("/ws")
async def websocket_realtime_events(websocket: WebSocket):
    """Authenticated WebSocket transport over the existing realtime hub.

    The access token is accepted as a query parameter because browsers cannot
    set arbitrary WebSocket Authorization headers. Production clients should
    prefer a short-lived token and TLS.
    """
    token = websocket.query_params.get("access_token")
    if not token:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    session = SessionLocal()
    connection = None
    lease = PresenceLease()
    lease_id = None
    lease_agent_user_id = None
    try:
        from app.api.auth import get_current_user
        user = await get_current_user(token=token, session=session)
        from app.identity import decode_identity_claims
        session_id = str(decode_identity_claims(token, expected_type="access")["sid"])
        requested_workspace_id = UUID(websocket.query_params["workspace_id"])
        principal = await PrincipalResolver(session).resolve(
            user=user, requested_workspace_id=requested_workspace_id
        )
        workspace_id = principal.workspace_id
        connection = await realtime_hub.register(user_id=workspace_id, scope=websocket.query_params.get("scope"))
        await websocket.send_json({"type": "realtime.connected", "workspace_id": str(workspace_id)})
        while True:
            receive_task = asyncio.create_task(websocket.receive())
            event_task = asyncio.create_task(connection.queue.get())
            done, pending = await asyncio.wait(
                {receive_task, event_task}, timeout=75, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            if not done:
                await websocket.send_json({"type": "realtime.heartbeat"})
                continue
            if event_task in done:
                event = event_task.result()
                if event is None:
                    break
                await websocket.send_json(event.model_dump(mode="json"))
                continue
            receive = receive_task.result()
            if receive.get("type") == "websocket.disconnect":
                break
            if receive.get("text"):
                import json
                message = json.loads(receive["text"])
                if message.get("type") == "agent.presence.heartbeat":
                    # Identity is derived from the authenticated token; clients
                    # cannot claim another agent's presence lease.
                    lease_agent_user_id = user.id
                    lease_id = await lease.heartbeat(
                        workspace_id=workspace_id, agent_user_id=user.id,
                        connection_id=lease_id or f"{session_id}:{uuid4()}",
                    )
                    from sqlalchemy import select
                    from app.domains.customer_service.models import CustomerServiceAgent
                    agent = await session.scalar(select(CustomerServiceAgent).where(
                        CustomerServiceAgent.user_id == workspace_id,
                        CustomerServiceAgent.agent_user_id == user.id,
                    ))
                    if agent is not None and agent.availability_source == "disconnect":
                        agent.availability = "available"
                        agent.availability_source = "manual"
                        await session.commit()
    except (WebSocketDisconnect, asyncio.TimeoutError, ValueError, KeyError):
        pass
    finally:
        if connection is not None:
            await realtime_hub.unregister(connection)
        if lease_id and lease_agent_user_id:
            await lease.release(workspace_id=workspace_id, agent_user_id=lease_agent_user_id, connection_id=lease_id)
            if not await lease.has_any(workspace_id=workspace_id, agent_user_id=lease_agent_user_id):
                from sqlalchemy import select
                from app.domains.customer_service.models import CustomerServiceAgent
                agent = await session.scalar(select(CustomerServiceAgent).where(
                    CustomerServiceAgent.user_id == workspace_id,
                    CustomerServiceAgent.agent_user_id == lease_agent_user_id,
                ))
                if agent is not None and agent.availability == "available":
                    agent.availability = "offline"
                    agent.availability_source = "disconnect"
                    await session.commit()
        await session.close()


__all__ = [
    "jobs_router",
    "schedules_router",
    "webhooks_router",
    "events_router",
    "realtime_router",
]
