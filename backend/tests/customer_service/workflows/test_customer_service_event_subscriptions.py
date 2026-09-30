from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.main import app
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.jobs.repository import JobRepository


class FakeUser:
    id = uuid4()
    email = "event-subscriptions@example.com"


def simple_workflow():
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "text": "Handled by event subscription",
                },
            },
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "trigger",
                "target": "response",
            },
        ],
    }


@pytest.mark.asyncio
async def test_create_and_list_customer_service_event_subscription():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "WhatsApp message workflow",
                    "event_type": "customer_service.omnichannel.message.received",
                    "channel": "whatsapp",
                    "workflow_json": simple_workflow(),
                },
            )

            assert created.status_code == 200
            assert created.json()["name"] == "WhatsApp message workflow"

            listed = await client.get("/customer-service/event-subscriptions")

            assert listed.status_code == 200
            assert any(
                item["name"] == "WhatsApp message workflow" for item in listed.json()
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_matching_event_subscription_enqueues_workflow_job():
    user_id = uuid4()

    async with SessionLocal() as db:
        from app.domains.customer_service.repositories.event_subscriptions import (
            CustomerServiceEventSubscriptionRepository,
        )

        await CustomerServiceEventSubscriptionRepository(db).create(
            user_id=user_id,
            name="Inbound WhatsApp workflow",
            event_type="customer_service.omnichannel.message.received",
            channel="whatsapp",
            workflow_json=simple_workflow(),
        )

        result = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type="customer_service.omnichannel.message.received",
            source="customer_service.omnichannel",
            payload={
                "conversation_id": str(uuid4()),
                "message_id": str(uuid4()),
                "channel": "whatsapp",
                "body": "hello from whatsapp",
            },
            dispatch=True,
        )

        handler_result = result["handler_results"][0]
        subscription_result = handler_result["subscriptions"]

        assert subscription_result["matched"] == 1
        assert len(subscription_result["enqueued"]) == 1

        job_id = subscription_result["enqueued"][0]["job_id"]
        job = await JobRepository(db).get(job_id)

        assert job is not None
        assert job.job_type == "workflow.run"
        assert job.payload["message"] == "hello from whatsapp"
        assert job.payload["extras"]["customer_service"] is True


@pytest.mark.asyncio
async def test_event_subscription_filters_skip_when_intent_does_not_match():
    user_id = uuid4()

    async with SessionLocal() as db:
        from app.domains.customer_service.repositories.event_subscriptions import (
            CustomerServiceEventSubscriptionRepository,
        )

        await CustomerServiceEventSubscriptionRepository(db).create(
            user_id=user_id,
            name="Refund only workflow",
            event_type="customer_service.omnichannel.message.received",
            channel="whatsapp",
            workflow_json=simple_workflow(),
            filters={
                "intent": "refund",
            },
        )

        result = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type="customer_service.omnichannel.message.received",
            source="customer_service.omnichannel",
            payload={
                "conversation_id": str(uuid4()),
                "message_id": str(uuid4()),
                "channel": "whatsapp",
                "body": "Where is my package?",
            },
            dispatch=True,
        )

        subscription_result = result["handler_results"][0]["subscriptions"]

        assert subscription_result["matched"] == 1
        assert subscription_result["filter_matched"] == 0
        assert subscription_result["selected"] == 0
        assert subscription_result["enqueued"] == []
        assert subscription_result["skipped"][0]["reason"] == "filters_not_matched"


@pytest.mark.asyncio
async def test_event_subscription_filters_enqueue_when_keywords_match():
    user_id = uuid4()

    async with SessionLocal() as db:
        from app.domains.customer_service.repositories.event_subscriptions import (
            CustomerServiceEventSubscriptionRepository,
        )

        await CustomerServiceEventSubscriptionRepository(db).create(
            user_id=user_id,
            name="VIP damaged workflow",
            event_type="customer_service.omnichannel.message.received",
            channel="instagram",
            workflow_json=simple_workflow(),
            filters={
                "intent": "damaged_product",
                "keywords": ["urgent", "damaged"],
            },
        )

        result = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type="customer_service.omnichannel.message.received",
            source="customer_service.omnichannel",
            payload={
                "conversation_id": str(uuid4()),
                "message_id": str(uuid4()),
                "channel": "instagram",
                "body": "This is urgent, my product arrived damaged",
            },
            dispatch=True,
        )

        subscription_result = result["handler_results"][0]["subscriptions"]

        assert subscription_result["matched"] == 1
        assert len(subscription_result["enqueued"]) == 1
        assert subscription_result["classification"]["intent"] == "damaged_product"


@pytest.mark.asyncio
async def test_get_update_and_delete_customer_service_event_subscription():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Manage me",
                    "event_type": "customer_service.omnichannel.message.received",
                    "channel": "whatsapp",
                    "workflow_json": simple_workflow(),
                },
            )
            assert created.status_code == 200
            subscription_id = created.json()["id"]

            fetched = await client.get(
                f"/customer-service/event-subscriptions/{subscription_id}",
            )
            assert fetched.status_code == 200
            assert fetched.json()["name"] == "Manage me"

            updated = await client.patch(
                f"/customer-service/event-subscriptions/{subscription_id}",
                json={
                    "name": "Managed subscription",
                    "is_active": False,
                    "filters": {"intent": "refund"},
                },
            )
            assert updated.status_code == 200
            assert updated.json()["name"] == "Managed subscription"
            assert updated.json()["is_active"] is False
            assert updated.json()["filters"]["intent"] == "refund"

            deleted = await client.delete(
                f"/customer-service/event-subscriptions/{subscription_id}",
            )
            assert deleted.status_code == 204

            missing = await client.get(
                f"/customer-service/event-subscriptions/{subscription_id}",
            )
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_exclusive_subscription_suppresses_fallback_and_enqueues_one_job():
    """
    A public widget message matching a dedicated exclusive workflow must
    suppress the broad website-chat fallback and persist exactly one job.
    """
    from httpx import ASGITransport, AsyncClient

    from app.api.auth import get_current_user
    from app.main import app

    class DispatchTestUser:
        def __init__(self):
            self.id = uuid4()
            self.email = f"dispatch-{self.id}@example.com"

    user = DispatchTestUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            fallback_response = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Website chat integration fallback",
                    "event_type": "customer.chat.message.created",
                    "channel": "website",
                    "workflow_json": simple_workflow(),
                    "filters": {},
                    "is_active": True,
                    "meta": {
                        "dispatch_mode": "fallback",
                        "dispatch_priority": 0,
                    },
                },
            )
            assert fallback_response.status_code == 200, fallback_response.text
            fallback = fallback_response.json()

            exclusive_response = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Dedicated custom integration workflow",
                    "event_type": "customer.chat.message.created",
                    "channel": "website",
                    "workflow_json": simple_workflow(),
                    "filters": {
                        "keywords": ["test-integration"],
                    },
                    "is_active": True,
                    "meta": {
                        "dispatch_mode": "exclusive",
                        "dispatch_priority": 100,
                    },
                },
            )
            assert exclusive_response.status_code == 200, exclusive_response.text
            exclusive = exclusive_response.json()

            settings_response = await client.get(
                "/customer-service/chat/widget/settings"
            )
            assert settings_response.status_code == 200, settings_response.text
            public_key = settings_response.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200, session_response.text
            session_id = session_response.json()["id"]

            message = "test-integration custom automation"

            message_response = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={"content": message},
            )
            assert message_response.status_code == 200, message_response.text

            body = message_response.json()
            dispatch = body["workflow_dispatch"]

            assert body["event_id"]
            assert dispatch["matched"] == 2
            assert dispatch["filter_matched"] == 2
            assert dispatch["selected"] == 1
            assert len(dispatch["enqueued"]) == 1

            enqueued = dispatch["enqueued"][0]

            assert enqueued["subscription_id"] == exclusive["id"]
            assert enqueued["job_type"] == "workflow.run"

            skipped_by_id = {
                item["subscription_id"]: item for item in dispatch["skipped"]
            }

            assert skipped_by_id[fallback["id"]] == {
                "subscription_id": fallback["id"],
                "reason": "fallback_suppressed",
                "dispatch_mode": "fallback",
                "dispatch_priority": 0,
            }

            jobs_response = await client.get("/jobs")
            assert jobs_response.status_code == 200, jobs_response.text

            matching_jobs = [
                job
                for job in jobs_response.json()
                if job["job_type"] == "workflow.run"
                and job["payload"].get("message") == message
            ]

            assert len(matching_jobs) == 1

            job = matching_jobs[0]

            assert job["payload"]["extras"]["subscription"] == {
                "id": exclusive["id"],
                "name": "Dedicated custom integration workflow",
            }
            assert job["payload"]["extras"]["event"]["payload"]["session_id"] == (
                session_id
            )
            assert job["payload"]["extras"]["event"]["payload"]["channel"] == (
                "website"
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)
