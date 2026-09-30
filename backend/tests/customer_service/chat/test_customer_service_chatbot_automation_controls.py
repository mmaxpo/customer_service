from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chatbot-controls@example.com"


@pytest.mark.asyncio
async def test_chatbot_automation_controls_are_saved_and_exposed_publicly():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            assert settings.status_code == 200
            public_key = settings.json()["public_key"]

            updated = await client.put(
                "/customer-service/chat/widget/settings",
                json={
                    "auto_answer_confidence_threshold": 0.82,
                    "human_handoff_enabled": True,
                    "human_handoff_message": "A human support agent will join shortly.",
                },
            )
            assert updated.status_code == 200, updated.text
            body = updated.json()

            assert body["auto_answer_confidence_threshold"] == 0.82
            assert body["human_handoff_enabled"] is True
            assert (
                body["human_handoff_message"]
                == "A human support agent will join shortly."
            )

            public = await client.get(
                f"/customer-service/chat/public/{public_key}/settings"
            )
            assert public.status_code == 200
            public_body = public.json()

            assert public_body["auto_answer_confidence_threshold"] == 0.82
            assert public_body["human_handoff_enabled"] is True
            assert (
                public_body["human_handoff_message"]
                == "A human support agent will join shortly."
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
