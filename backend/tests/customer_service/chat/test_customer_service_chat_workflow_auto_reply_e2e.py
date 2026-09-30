from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.main import app
from app.platform.jobs.handlers import JobContext
from app.platform.jobs.repository import JobRepository
from app.runtime.workflow_jobs import run_workflow_job


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chat-auto-reply@example.com"


@pytest.mark.asyncio
async def test_chat_event_workflow_can_reply_back_to_chat_and_inbox():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            workflow = {
                "name": "Chat auto reply workflow",
                "nodes": [
                    {
                        "id": "trigger",
                        "data": {
                            "nodeType": "trigger.message",
                        },
                    },
                    {
                        "id": "set_reply",
                        "data": {
                            "nodeType": "set.variable",
                            "key": "reply",
                            "value": "Hello from automated workflow",
                        },
                    },
                    {
                        "id": "reply_chat",
                        "data": {
                            "nodeType": "reply.customer_chat",
                            "session_id_from": "extras",
                            "session_id_key": "session_id",
                            "message_from": "vars",
                            "message_key": "reply",
                        },
                    },
                    {
                        "id": "response",
                        "data": {
                            "nodeType": "response",
                        },
                    },
                ],
                "edges": [
                    {"source": "trigger", "target": "set_reply"},
                    {"source": "set_reply", "target": "reply_chat"},
                    {"source": "reply_chat", "target": "response"},
                ],
            }

            subscription = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Website chat auto reply",
                    "event_type": "customer.chat.message.created",
                    "workflow_json": workflow,
                    "filters": {"keywords": ["hello"]},
                    "is_active": True,
                },
            )
            assert subscription.status_code == 200

            settings = await client.get("/customer-service/chat/widget/settings")
            assert settings.status_code == 200
            public_key = settings.json()["public_key"]

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
                    "content": "hello, can you help me?",
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

            result = await run_workflow_job(
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
                and msg["content"] == "Hello from automated workflow"
                for msg in chat_messages.json()
            )

            detail = await client.get(
                f"/customer-service/conversations/{session['conversation_id']}"
            )
            assert detail.status_code == 200

            assert any(
                msg["sender_type"] == "ai"
                and msg["body"] == "Hello from automated workflow"
                and msg["meta"]["source"] == "customer_chat"
                for msg in detail.json()["messages"]
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
