from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import get_db
from app.main import app
from app.platform.events.event_bus import PlatformEventBus
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.events.registry import EventHandlerRegistry
from app.platform.jobs.service import JobService


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_event_bus_persists_and_dispatches_handler():
    user_id = uuid4()
    registry = EventHandlerRegistry()

    seen = {}

    async def handler(event, ctx):
        seen["event_type"] = event.event_type
        seen["payload"] = event.payload
        return {"handled": True}

    registry.subscribe("test.created", handler)

    async for db in get_db():
        result = await PlatformEventBus(db, registry=registry).publish(
            user_id=user_id,
            event_type="test.created",
            source="test",
            payload={"hello": "world"},
        )

        assert result["event"].event_type == "test.created"
        assert result["handler_results"] == [{"handled": True}]
        assert seen["payload"] == {"hello": "world"}

        break


@pytest.mark.asyncio
async def test_publish_workflow_requested_enqueues_workflow_job():
    user_id = uuid4()

    workflow = {
        "nodes": [],
        "edges": [],
    }

    async for db in get_db():
        result = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type="workflow.requested",
            source="test",
            payload={
                "workflow": workflow,
                "message": "from event",
            },
        )

        handler_result = result["handler_results"][0]

        assert handler_result["job_type"] == "workflow.run"
        assert handler_result["enqueued_job_id"]

        job = await JobService(db).get(
            job_id=handler_result["enqueued_job_id"],
            user_id=user_id,
        )
        assert job.payload["event"]["event_type"] == "workflow.requested"

        break


@pytest.mark.asyncio
async def test_events_api_publish_and_list():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/events",
                json={
                    "event_type": "custom.event",
                    "source": "test",
                    "payload": {"x": 1},
                },
            )

            assert created.status_code == 200
            assert created.json()["event_type"] == "custom.event"

            listed = await client.get("/events")

            assert listed.status_code == 200
            assert any(item["id"] == created.json()["id"] for item in listed.json())

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_events_api_cannot_dispatch_internal_workflow_event():
    from sqlalchemy import select

    from app.core.session import SessionLocal
    from app.models.models import PlatformJob

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    marker = f"CORE-4.8-{uuid4()}"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/events",
                json={
                    "event_type": "workflow.requested",
                    "source": "http-test",
                    "payload": {
                        "workflow": {
                            "nodes": [],
                            "edges": [],
                        },
                        "message": marker,
                    },
                    "meta": {
                        "proof": "http-must-not-dispatch",
                    },
                },
            )

        assert created.status_code == 200

        body = created.json()

        assert body["user_id"] == str(user.id)
        assert body["event_type"] == "workflow.requested"
        assert body["payload"]["message"] == marker

        async with SessionLocal() as db:
            jobs = list(
                (
                    await db.execute(
                        select(PlatformJob).where(
                            PlatformJob.user_id == user.id,
                            PlatformJob.job_type == "workflow.run",
                        )
                    )
                )
                .scalars()
                .all()
            )

        injected_jobs = [
            job for job in jobs if (job.payload or {}).get("message") == marker
        ]

        assert injected_jobs == []

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_events_api_get_rejects_cross_user_access():
    from app.core.session import SessionLocal
    from app.platform.events.event_store import PlatformEventStore

    owner = FakeUser()
    attacker = FakeUser()

    async with SessionLocal() as db:
        foreign_event = await PlatformEventStore(db).append(
            user_id=owner.id,
            event_type=f"test.private.{uuid4()}",
            source="test",
            payload={
                "secret_marker": "owner-private-event",
            },
            meta={
                "secret_meta": "owner-private-meta",
            },
        )

        foreign_event_id = foreign_event.id

    app.dependency_overrides[get_current_user] = lambda: attacker

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/events/{foreign_event_id}")

            assert response.status_code == 404
            assert response.json() == {
                "detail": "Event not found",
            }

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_events_api_get_allows_owner_access():
    from app.core.session import SessionLocal
    from app.platform.events.event_store import PlatformEventStore

    owner = FakeUser()

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).append(
            user_id=owner.id,
            event_type=f"test.owner.{uuid4()}",
            source="test",
            payload={
                "marker": "owner-visible",
            },
            meta={
                "proof": "owner-access",
            },
        )

        event_id = event.id

    app.dependency_overrides[get_current_user] = lambda: owner

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/events/{event_id}")

            assert response.status_code == 200

            body = response.json()

            assert body["id"] == str(event_id)
            assert body["user_id"] == str(owner.id)
            assert body["payload"] == {
                "marker": "owner-visible",
            }
            assert body["meta"] == {
                "proof": "owner-access",
            }

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
