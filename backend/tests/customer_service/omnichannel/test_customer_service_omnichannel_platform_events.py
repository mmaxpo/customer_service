from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.platform.events.event_store import PlatformEventStore
from app.api.auth import get_current_user


class FakeUser:
    id = uuid4()
    email = "omni-events@example.com"


@pytest.mark.asyncio
async def test_omnichannel_inbound_publishes_platform_event():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "events-account-1",
                    "external_thread_id": "events-thread-1",
                    "external_message_id": "events-message-1",
                    "external_customer_id": "events-customer-1",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "I need help with my damaged order",
                },
            )

        assert response.status_code == 200

        async with SessionLocal() as db:
            events = await PlatformEventStore(db).list_by_type(
                event_type="customer_service.omnichannel.message.received",
                limit=20,
            )

        matching = [
            event
            for event in events
            if event.user_id == user.id
            and event.payload.get("external_message_id") == "events-message-1"
        ]

        assert matching
        assert matching[0].source == "customer_service.omnichannel"
        assert matching[0].payload["channel"] == "whatsapp"
        assert (
            matching[0].payload["conversation_id"] == response.json()["conversation_id"]
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_omnichannel_delivery_event_publishes_platform_event():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "instagram",
                    "external_account_id": "events-account-2",
                    "external_thread_id": "events-thread-2",
                    "external_message_id": "events-message-2",
                    "external_customer_id": "events-customer-2",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "hello",
                },
            )
            assert inbound.status_code == 200

            delivery = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json={
                    "channel": "instagram",
                    "external_account_id": "events-account-2",
                    "external_message_id": "events-message-2",
                    "delivery_status": "read",
                },
            )

        assert delivery.status_code == 200

        async with SessionLocal() as db:
            events = await PlatformEventStore(db).list_by_type(
                event_type="customer_service.omnichannel.delivery.updated",
                limit=20,
            )

        matching = [
            event
            for event in events
            if event.user_id == user.id
            and event.payload.get("external_message_id") == "events-message-2"
        ]

        assert matching
        assert matching[0].payload["delivery_status"] == "read"
        assert matching[0].payload["updated"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
