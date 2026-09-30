from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chat-automation-settings@example.com"


@pytest.mark.asyncio
async def test_chat_widget_settings_attach_and_disable_workflow_automation():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seed = await client.post(
                "/customer-service/workflow-templates/seed-shopify"
            )
            assert seed.status_code == 200

            templates = await client.get("/customer-service/workflow-templates")
            assert templates.status_code == 200

            published = [
                template
                for template in templates.json()
                if template["status"] == "published"
            ]
            assert published

            template_id = published[0]["id"]

            updated = await client.put(
                "/customer-service/chat/widget/settings",
                json={
                    "workflow_template_id": template_id,
                    "auto_answer_enabled": True,
                },
            )
            assert updated.status_code == 200
            assert updated.json()["workflow_template_id"] == template_id
            assert updated.json()["auto_answer_enabled"] is True

            subscriptions = await client.get("/customer-service/event-subscriptions")
            assert subscriptions.status_code == 200

            auto = [
                item
                for item in subscriptions.json()
                if item["name"] == "Website chat automation"
            ]

            assert len(auto) == 1
            assert auto[0]["event_type"] == "customer.chat.message.created"
            assert auto[0]["channel"] == "website"
            assert auto[0]["workflow_template_id"] == template_id
            assert auto[0]["is_active"] is True

            disabled = await client.put(
                "/customer-service/chat/widget/settings",
                json={
                    "auto_answer_enabled": False,
                },
            )
            assert disabled.status_code == 200
            assert disabled.json()["auto_answer_enabled"] is False

            subscriptions = await client.get("/customer-service/event-subscriptions")
            assert subscriptions.status_code == 200

            auto = [
                item
                for item in subscriptions.json()
                if item["name"] == "Website chat automation"
            ]

            assert len(auto) == 1
            assert auto[0]["is_active"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)
