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
async def test_seed_shopify_workflow_templates_is_idempotent_and_listed():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/customer-service/workflow-templates/seed-shopify"
            )

            assert first.status_code == 200

            first_data = first.json()

            assert first_data["created_count"] + first_data["existing_count"] >= 4

            second = await client.post(
                "/customer-service/workflow-templates/seed-shopify"
            )

            assert second.status_code == 200

            second_data = second.json()

            assert second_data["created_count"] == 0
            assert second_data["existing_count"] >= 4

            listed = await client.get("/customer-service/workflow-templates")

            assert listed.status_code == 200

            names = {item["name"] for item in listed.json()}

            assert "Shopify Refund Request Workflow" in names
            assert "Shopify Order Cancellation Workflow" in names
            assert "Shopify Shipping Status Workflow" in names
            assert "Shopify Damaged Item Workflow" in names

            shopify_templates = [
                item for item in listed.json() if item["category"] == "shopify_support"
            ]

            assert all(item["scope"] == "system" for item in shopify_templates)
            assert all(item["status"] == "published" for item in shopify_templates)

    finally:
        app.dependency_overrides.pop(get_current_user, None)
