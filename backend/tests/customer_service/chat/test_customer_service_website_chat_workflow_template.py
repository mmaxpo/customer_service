from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "website-chat-template@example.com"


@pytest.mark.asyncio
async def test_seed_website_chat_ai_reply_workflow_template():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seeded = await client.post(
                "/customer-service/workflow-templates/seed-website-chat"
            )
            assert seeded.status_code == 200

            body = seeded.json()
            assert body["created_count"] + body["existing_count"] >= 1

            templates = await client.get("/customer-service/workflow-templates")
            assert templates.status_code == 200

            website_chat = [
                template
                for template in templates.json()
                if template["name"] == "Website Chat AI Reply Workflow"
            ]

            assert len(website_chat) == 1

            workflow = website_chat[0]["workflow_json"]
            node_types = {node["data"]["nodeType"] for node in workflow["nodes"]}

            assert "trigger.message" in node_types
            assert "llm.generate" in node_types
            assert "reply.customer_chat" in node_types
            assert "response" in node_types
            assert website_chat[0]["status"] == "published"
            assert website_chat[0]["scope"] == "system"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
