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
async def test_shopify_connect_and_get_order():
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
                    "shop_domain": "https://Example.myshopify.com/",
                    "access_token": "test-token",
                },
            )

            assert connect.status_code == 200
            assert connect.json()["shop_domain"] == "example.myshopify.com"

            order = await client.get("/customer-service/shopify/orders/1001")

            assert order.status_code == 200

            data = order.json()

            assert data["order_id"] == "1001"
            assert data["order_name"] == "#1001"
            assert data["payload"]["financial_status"] == "paid"
            assert data["payload"]["fulfillment_status"] == "fulfilled"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_shopify_order_requires_connection():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            order = await client.get("/customer-service/shopify/orders/1001")

            assert order.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_workspace_can_keep_multiple_stores_and_requires_selection():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.post(
                "/customer-service/shopify/connect",
                json={"shop_domain": "store-a.myshopify.com", "access_token": "a"},
            )
            second = await client.post(
                "/customer-service/shopify/connect",
                json={"shop_domain": "store-b.myshopify.com", "access_token": "b"},
            )
            assert first.status_code == second.status_code == 200

            stores = await client.get("/customer-service/shopify/connections")
            assert stores.status_code == 200
            assert {store["shop_domain"] for store in stores.json()} == {
                "store-a.myshopify.com",
                "store-b.myshopify.com",
            }
            assert {store["status"] for store in stores.json()} == {"connected"}

            ambiguous = await client.get("/customer-service/shopify/orders/1001")
            assert ambiguous.status_code == 409
            assert ambiguous.json()["detail"] == "shopify_store_selection_required"

            selected = await client.get(
                f"/customer-service/shopify/orders/1001?connection_id={first.json()['id']}"
            )
            assert selected.status_code == 200

            reconnected = await client.post(
                "/customer-service/shopify/connect",
                json={
                    "shop_domain": "https://store-a.myshopify.com/",
                    "access_token": "new-a",
                },
            )
            assert reconnected.status_code == 200
            assert reconnected.json()["id"] == first.json()["id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_shopify_support_actions_prepare_safe_outcomes():
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

            refund = await client.post(
                "/customer-service/shopify/orders/1001/actions/refund",
                json={
                    "order_ref": "1001",
                    "reason": "Damaged item",
                    "amount": "99.00",
                    "idempotency_key": "phase3-refund-1001",
                },
            )
            assert refund.status_code == 200
            assert refund.json()["action"] == "refund"
            assert refund.json()["status"] == "prepared"

            cancel = await client.post(
                "/customer-service/shopify/orders/1001/actions/cancel",
                json={
                    "order_ref": "1001",
                    "reason": "Customer requested cancellation",
                    "idempotency_key": "phase3-cancel-1001",
                },
            )
            assert cancel.status_code == 200
            assert cancel.json()["status"] == "blocked"

            shipping = await client.post(
                "/customer-service/shopify/orders/1001/actions/shipping_status",
                json={"order_ref": "1001"},
            )
            assert shipping.status_code == 200
            assert shipping.json()["payload"]["fulfillment_status"] == "fulfilled"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_shopify_unsupported_action_returns_422():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/customer-service/shopify/connect",
                json={"shop_domain": "example.myshopify.com"},
            )

            response = await client.post(
                "/customer-service/shopify/orders/1001/actions/unknown",
                json={"order_ref": "1001"},
            )

            assert response.status_code == 422

    finally:
        app.dependency_overrides.pop(get_current_user, None)
