from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_repeated_shopify_seed_does_not_duplicate_templates_or_subscriptions():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            for _ in range(5):
                templates_seed = await client.post(
                    "/customer-service/workflow-templates/seed-shopify"
                )
                assert templates_seed.status_code == 200

                subscriptions_seed = await client.post(
                    "/customer-service/event-subscriptions/seed-shopify"
                )
                assert subscriptions_seed.status_code == 200

            templates = await client.get("/customer-service/workflow-templates")
            assert templates.status_code == 200

            shopify_template_names = [
                item["name"]
                for item in templates.json()
                if item["category"] == "shopify_support" and item["scope"] == "system"
            ]

            assert len(shopify_template_names) == len(set(shopify_template_names))
            assert len(shopify_template_names) == 4

            subscriptions = await client.get("/customer-service/event-subscriptions")
            assert subscriptions.status_code == 200

            shopify_subscription_names = [
                item["name"]
                for item in subscriptions.json()
                if item["meta"].get("source") == "shopify_template_seed"
            ]

            assert len(shopify_subscription_names) == len(
                set(shopify_subscription_names)
            )
            assert len(shopify_subscription_names) == 4

    finally:
        app.dependency_overrides.pop(get_current_user, None)
