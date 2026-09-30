from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.role = "owner"


async def _conversation_with_message(client, body: str):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Shopify Action Customer",
                "email": f"{uuid4()}@test.com",
                "phone": "111",
            },
        )
    ).json()

    conversation = (
        await client.post(
            "/customer-service/conversations/",
            json={
                "customer_id": customer["id"],
                "channel": "chat",
                "subject": "shopify action",
            },
        )
    ).json()

    await client.post(
        f"/customer-service/conversations/{conversation['id']}/messages",
        json={
            "sender_type": "customer",
            "body": body,
        },
    )

    return conversation


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected_action"),
    [
        ("I want a refund for order #1001", "shopify_refund"),
        ("Please cancel order #1002", "shopify_cancel"),
        ("Order #1003 arrived damaged and broken", "shopify_damaged_item"),
        ("Where is my order #1004? It is late", "shopify_track_order"),
    ],
)
async def test_shopify_suggested_actions_generated_from_order_ref(
    message,
    expected_action,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation = await _conversation_with_message(client, message)

            response = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )

            assert response.status_code == 200

            actions = response.json()
            action_types = [action["action_type"] for action in actions]

            assert expected_action in action_types

            action = next(
                item for item in actions if item["action_type"] == expected_action
            )

            assert action["source"] == "shopify"
            assert action["payload"]["order_ref"].startswith("#")

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_shopify_refund_not_generated_without_order_ref():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation = await _conversation_with_message(
                client, "I want a refund please"
            )

            response = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )

            assert response.status_code == 200

            actions = response.json()

            assert "shopify_refund" not in [a["action_type"] for a in actions]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_shopify_cancel_action_execute_flow():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            connect = await client.post(
                "/customer-service/shopify/connect",
                json={
                    "shop_domain": "example.myshopify.com",
                    "access_token": "token",
                },
            )

            assert connect.status_code == 200

            conversation = await _conversation_with_message(
                client, "Please cancel order #1002"
            )

            generated = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )

            assert generated.status_code == 200

            action = next(
                item
                for item in generated.json()
                if item["action_type"] == "shopify_cancel"
            )

            accepted = await client.post(
                f"/customer-service/suggested-actions/{action['id']}/accept"
            )

            assert accepted.status_code == 200

            executed = await client.post(
                f"/customer-service/suggested-actions/{action['id']}/execute",
                json={},
            )

            assert executed.status_code == 409
            assert "fulfilled" in executed.json()["detail"].lower()

    finally:
        app.dependency_overrides.pop(get_current_user, None)
