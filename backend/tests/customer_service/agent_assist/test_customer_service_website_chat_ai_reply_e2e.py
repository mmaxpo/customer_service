from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user, get_current_verified_user
from app.core.session import SessionLocal
from app.main import app
from app.platform.jobs.handlers import JobContext
from app.platform.jobs.repository import JobRepository
from app.runtime import workflow_jobs


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "website-chat-ai-reply@example.com"
        self.role = "owner"


class FakeGenerateLlm:
    async def generate(self, **kwargs):
        return SimpleNamespace(
            text="AI reply from seeded website chat workflow",
            model="fake-test-model",
            usage={"test": True},
        )


@pytest.mark.asyncio
async def test_seeded_website_chat_ai_reply_workflow_replies_to_widget_and_inbox(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_verified_user] = lambda: user

    monkeypatch.setattr(
        workflow_jobs,
        "build_tools",
        lambda: SimpleNamespace(llm=FakeGenerateLlm()),
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seeded = await client.post(
                "/customer-service/workflow-templates/seed-website-chat"
            )
            assert seeded.status_code == 200

            templates = await client.get("/customer-service/workflow-templates")
            assert templates.status_code == 200

            website_chat_template = next(
                template
                for template in templates.json()
                if template["name"] == "Website Chat AI Reply Workflow"
            )

            updated_settings = await client.put(
                "/customer-service/chat/widget/settings",
                json={
                    "auto_answer_enabled": True,
                    "workflow_template_id": website_chat_template["id"],
                    "auto_answer_confidence_threshold": 0.75,
                    "human_handoff_enabled": True,
                    "human_handoff_message": "A human support agent will join shortly.",
                },
            )
            assert updated_settings.status_code == 200
            public_key = updated_settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200
            session = session_response.json()

            message_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions/{session['id']}/messages",
                json={
                    "content": "Can you help me with my order?",
                },
            )
            assert message_response.status_code == 200

            dispatch = message_response.json()["workflow_dispatch"]
            assert dispatch["matched"] == 1
            assert len(dispatch["enqueued"]) == 1

            job_id = dispatch["enqueued"][0]["job_id"]

        async with SessionLocal() as db:
            job = await JobRepository(db).get(job_id)
            assert job is not None

            result = await workflow_jobs.run_workflow_job(
                payload=job.payload,
                ctx=JobContext(db=db, job=job, worker_id="test-worker"),
            )

            assert isinstance(result, dict)
            assert result.get("meta", {}).get("status") in {
                "ok",
                "completed",
                "success",
                None,
            }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            chat_messages = await client.get(
                f"/customer-service/chat/public/{public_key}/sessions/{session['id']}/messages"
            )
            assert chat_messages.status_code == 200

            assert any(
                msg["role"] == "assistant"
                and msg["content"] == "AI reply from seeded website chat workflow"
                for msg in chat_messages.json()
            )

            detail = await client.get(
                f"/customer-service/conversations/{session['conversation_id']}"
            )
            assert detail.status_code == 200

            assert any(
                msg["sender_type"] == "ai"
                and msg["body"] == "AI reply from seeded website chat workflow"
                and msg["meta"]["source"] == "customer_chat"
                for msg in detail.json()["messages"]
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_verified_user, None)
