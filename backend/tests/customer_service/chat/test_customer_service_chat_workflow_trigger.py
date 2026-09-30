import asyncio

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chat-workflow@example.com"


@pytest.mark.asyncio
async def test_public_chat_message_publishes_event_and_enqueues_matching_workflow():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            subscription = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Chat custom automation workflow",
                    "event_type": "customer.chat.message.created",
                    "workflow_json": {
                        "name": "Chat custom automation workflow",
                        "nodes": [
                            {
                                "id": "trigger",
                                "data": {"nodeType": "trigger.message"},
                            }
                        ],
                        "edges": [],
                    },
                    "filters": {"keywords": ["custom-automation"]},
                    "is_active": True,
                },
            )
            assert subscription.status_code == 200

            settings_response = await client.get(
                "/customer-service/chat/widget/settings"
            )
            assert settings_response.status_code == 200
            public_key = settings_response.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200
            session_id = session_response.json()["id"]

            message_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions/{session_id}/messages",
                json={
                    "content": "Please run custom-automation for this message",
                },
            )
            assert message_response.status_code == 200

            body = message_response.json()
            assert body["event_id"]
            assert body["workflow_dispatch"]["matched"] == 1
            assert len(body["workflow_dispatch"]["enqueued"]) == 1
            assert (
                body["workflow_dispatch"]["enqueued"][0]["job_type"] == "workflow.run"
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_public_chat_message_retry_is_idempotent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            subscription = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Idempotent custom automation workflow",
                    "event_type": "customer.chat.message.created",
                    "workflow_json": {
                        "name": "Idempotent custom automation workflow",
                        "nodes": [
                            {
                                "id": "trigger",
                                "data": {
                                    "nodeType": "trigger.message"
                                },
                            }
                        ],
                        "edges": [],
                    },
                    "filters": {
                        "keywords": ["idempotent-custom-automation"]
                    },
                    "is_active": True,
                },
            )
            assert subscription.status_code == 200

            settings = await client.get(
                "/customer-service/chat/widget/settings"
            )
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
            session_id = session_response.json()["id"]

            request_payload = {
                "content": (
                    "Please process idempotent-custom-automation request"
                ),
                "client_message_id": f"client-{uuid4()}",
            }

            first = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json=request_payload,
            )
            second = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json=request_payload,
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            first_body = first.json()
            second_body = second.json()

            assert first_body["idempotent_replay"] is False
            assert second_body["idempotent_replay"] is True

            assert second_body["id"] == first_body["id"]
            assert (
                second_body["inbox_message_id"]
                == first_body["inbox_message_id"]
            )
            assert (
                second_body["event_id"]
                == first_body["event_id"]
            )
            assert (
                second_body["workflow_dispatch"]
                == first_body["workflow_dispatch"]
            )

            messages = await client.get(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                )
            )
            assert messages.status_code == 200

            matching_messages = [
                item
                for item in messages.json()
                if item["role"] == "customer"
                and item["content"]
                == request_payload["content"]
            ]
            assert len(matching_messages) == 1

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            matching_jobs = [
                job
                for job in jobs.json()
                if job["job_type"] == "workflow.run"
                and job["payload"].get("message")
                == request_payload["content"]
            ]
            assert len(matching_jobs) == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_concurrent_public_chat_message_retry_is_idempotent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            subscription = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Concurrent idempotent custom automation workflow",
                    "event_type": "customer.chat.message.created",
                    "workflow_json": {
                        "name": "Concurrent idempotent custom automation workflow",
                        "nodes": [
                            {
                                "id": "trigger",
                                "data": {
                                    "nodeType": "trigger.message",
                                },
                            }
                        ],
                        "edges": [],
                    },
                    "filters": {
                        "keywords": [
                            "concurrent-idempotent-custom-automation"
                        ],
                    },
                    "is_active": True,
                },
            )
            assert subscription.status_code == 200

            settings = await client.get(
                "/customer-service/chat/widget/settings"
            )
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
            session_id = session_response.json()["id"]

            payload = {
                "content": (
                    "Please process "
                    "concurrent-idempotent-custom-automation request"
                ),
                "client_message_id": f"client-{uuid4()}",
            }

            url = (
                f"/customer-service/chat/public/{public_key}"
                f"/sessions/{session_id}/messages"
            )

            first, second = await asyncio.gather(
                client.post(url, json=payload),
                client.post(url, json=payload),
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            responses = [first.json(), second.json()]

            assert sorted(
                response["idempotent_replay"]
                for response in responses
            ) == [False, True]

            created = next(
                response
                for response in responses
                if response["idempotent_replay"] is False
            )
            replayed = next(
                response
                for response in responses
                if response["idempotent_replay"] is True
            )

            assert replayed["id"] == created["id"]
            assert (
                replayed["conversation_id"]
                == created["conversation_id"]
            )
            assert (
                replayed["inbox_message_id"]
                == created["inbox_message_id"]
            )
            assert replayed["event_id"] == created["event_id"]
            assert (
                replayed["workflow_dispatch"]
                == created["workflow_dispatch"]
            )

            chat_messages = await client.get(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                )
            )
            assert chat_messages.status_code == 200

            matching_messages = [
                message
                for message in chat_messages.json()
                if message["role"] == "customer"
                and message["content"] == payload["content"]
            ]
            assert len(matching_messages) == 1

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            matching_jobs = [
                job
                for job in jobs.json()
                if job["job_type"] == "workflow.run"
                and job["payload"].get("message")
                == payload["content"]
            ]
            assert len(matching_jobs) == 1

            dispatch = created["workflow_dispatch"]
            assert dispatch["matched"] == 1
            assert len(dispatch["enqueued"]) == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
