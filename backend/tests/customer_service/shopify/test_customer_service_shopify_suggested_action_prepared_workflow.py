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


@pytest.mark.asyncio
async def test_shopify_refund_suggested_action_contains_prepared_workflow():
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
                    "access_token": "test-token",
                },
            )
            assert connect.status_code == 200

            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Prepared Workflow Customer",
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
                        "subject": "refund",
                    },
                )
            ).json()

            message = await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "I want a refund for order #1001",
                },
            )
            assert message.status_code == 200

            generated = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )
            assert generated.status_code == 200

            actions = generated.json()

            refund_action = next(
                action
                for action in actions
                if action["action_type"] == "shopify_refund"
            )

            payload = refund_action["payload"]

            assert payload["order_ref"] == "#1001"
            assert payload["reason"] == "refund_request"
            assert "prepared_workflow" in payload

            prepared = payload["prepared_workflow"]

            assert prepared["action"] == "refund"
            assert prepared["order_id"] == "#1001"
            assert prepared["workflow"]["workflow_type"] == "refund"
            assert prepared["workflow"]["next_action"] == "approval_required"
            assert prepared["workflow"]["requires_approval"] is True
            assert prepared["context"]["is_paid"] is True

    finally:
        app.dependency_overrides.pop(get_current_user, None)
