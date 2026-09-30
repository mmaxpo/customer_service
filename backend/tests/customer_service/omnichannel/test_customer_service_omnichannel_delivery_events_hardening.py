from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models import CustomerServiceExternalMessageLink
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "delivery-events-hardening@example.com"


async def _create_outbound_message(client, channel="generic"):
    inbound = await client.post(
        "/customer-service/omnichannel/inbound",
        json={
            "channel": channel,
            "external_account_id": f"{channel}-acct-{uuid4()}",
            "external_thread_id": f"{channel}-thread-{uuid4()}",
            "external_message_id": f"{channel}-inbound-{uuid4()}",
            "external_customer_id": f"{channel}-customer-{uuid4()}",
            "customer_email": f"{uuid4()}@example.com",
            "body": "Hello",
        },
    )
    assert inbound.status_code == 200

    conversation_id = inbound.json()["conversation_id"]
    external_account_id = f"{channel}-acct-outbound-{uuid4()}"

    outbound = await client.post(
        "/customer-service/omnichannel/outbound",
        json={
            "conversation_id": conversation_id,
            "body": "Hello back",
            "sender_type": "agent",
            "idempotency_key": f"delivery-event-key-{uuid4()}",
            "external_account_id": external_account_id,
        },
    )

    assert outbound.status_code == 200
    data = outbound.json()

    return {
        "channel": data["channel"],
        "external_account_id": data["external_account_id"],
        "external_message_id": data["external_message_id"],
        "message_id": data["message_id"],
    }


async def _get_link(user_id, *, channel, external_account_id, external_message_id):
    async with SessionLocal() as db:
        result = await db.execute(
            select(CustomerServiceExternalMessageLink).where(
                CustomerServiceExternalMessageLink.user_id == user_id,
                CustomerServiceExternalMessageLink.channel == channel,
                CustomerServiceExternalMessageLink.external_account_id
                == external_account_id,
                CustomerServiceExternalMessageLink.external_message_id
                == external_message_id,
            )
        )
        return result.scalar_one()


@pytest.mark.asyncio
async def test_delivery_event_updates_outbound_message_status():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            msg = await _create_outbound_message(client)

            response = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json={
                    "channel": msg["channel"],
                    "external_account_id": msg["external_account_id"],
                    "external_message_id": msg["external_message_id"],
                    "delivery_status": "delivered",
                    "event_id": f"evt-{uuid4()}",
                    "raw_payload": {"provider_status": "delivered"},
                },
            )

            assert response.status_code == 200
            assert response.json()["delivery_status"] == "delivered"

            link = await _get_link(
                user.id,
                channel=msg["channel"],
                external_account_id=msg["external_account_id"],
                external_message_id=msg["external_message_id"],
            )

            assert link.delivery_status == "delivered"
            assert link.meta["omnichannel"]["delivery_status"] == "delivered"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_duplicate_delivery_event_is_idempotent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            msg = await _create_outbound_message(client)
            event_id = f"evt-{uuid4()}"

            payload = {
                "channel": msg["channel"],
                "external_account_id": msg["external_account_id"],
                "external_message_id": msg["external_message_id"],
                "delivery_status": "delivered",
                "event_id": event_id,
                "raw_payload": {"provider_status": "delivered"},
            }

            first = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json=payload,
            )
            second = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json=payload,
            )

            assert first.status_code == 200
            assert second.status_code == 200
            assert second.json()["delivery_status"] == first.json()["delivery_status"]

            link = await _get_link(
                user.id,
                channel=msg["channel"],
                external_account_id=msg["external_account_id"],
                external_message_id=msg["external_message_id"],
            )

            events = link.meta["omnichannel"].get("delivery_events", [])
            matching = [event for event in events if event.get("event_id") == event_id]

            assert len(matching) == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_delivery_status_never_downgrades_from_read_to_delivered():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            msg = await _create_outbound_message(client)

            read = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json={
                    "channel": msg["channel"],
                    "external_account_id": msg["external_account_id"],
                    "external_message_id": msg["external_message_id"],
                    "delivery_status": "read",
                    "event_id": f"evt-read-{uuid4()}",
                },
            )
            delivered = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json={
                    "channel": msg["channel"],
                    "external_account_id": msg["external_account_id"],
                    "external_message_id": msg["external_message_id"],
                    "delivery_status": "delivered",
                    "event_id": f"evt-delivered-{uuid4()}",
                },
            )

            assert read.status_code == 200
            assert delivered.status_code == 200
            assert delivered.json()["delivery_status"] == "read"

            link = await _get_link(
                user.id,
                channel=msg["channel"],
                external_account_id=msg["external_account_id"],
                external_message_id=msg["external_message_id"],
            )

            assert link.delivery_status == "read"
            assert link.meta["omnichannel"]["delivery_status"] == "read"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_delivery_event_for_unknown_external_message_returns_404():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json={
                    "channel": "generic",
                    "external_account_id": f"acct-{uuid4()}",
                    "external_message_id": f"missing-{uuid4()}",
                    "delivery_status": "delivered",
                    "event_id": f"evt-{uuid4()}",
                },
            )

            assert response.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
