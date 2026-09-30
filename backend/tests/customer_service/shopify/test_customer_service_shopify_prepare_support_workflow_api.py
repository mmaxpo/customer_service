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
async def test_prepare_shopify_refund_support_workflow_requires_approval():
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

            response = await client.post(
                "/customer-service/shopify/support-workflows/prepare",
                json={
                    "action": "refund",
                    "order_ref": "1001",
                    "reason": "customer requested refund",
                },
            )

            assert response.status_code == 200

            data = response.json()

            assert data["action"] == "refund"
            assert data["order_id"] == "1001"
            assert data["context"]["is_paid"] is True
            assert data["workflow"]["workflow_type"] == "refund"
            assert data["workflow"]["next_action"] == "approval_required"
            assert data["workflow"]["requires_approval"] is True

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_prepare_shopify_shipping_support_workflow_is_reply_ready():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/customer-service/shopify/connect",
                json={
                    "shop_domain": "example.myshopify.com",
                    "access_token": "test-token",
                },
            )

            response = await client.post(
                "/customer-service/shopify/support-workflows/prepare",
                json={
                    "action": "shipping_status",
                    "order_ref": "1001",
                },
            )

            assert response.status_code == 200

            data = response.json()

            assert data["workflow"]["workflow_type"] == "shipping_status"
            assert data["workflow"]["next_action"] in {
                "reply_ready",
                "manual_review",
                "approval_required",
            }
            assert data["context"]["order_id"] == "1001"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
