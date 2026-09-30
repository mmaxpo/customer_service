from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_ai_reply_suggested_action_execution_persists_quality_metadata(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    async def fake_search_context(self, *, user_id, query, k=5):
        return {
            "query": query,
            "context": "[1] Refund Policy\\nRefunds are reviewed within 3 business days.",
            "hits": [
                {
                    "doc_id": "refund-policy",
                    "title": "Refund Policy",
                    "content": "Refunds are reviewed within 3 business days.",
                    "score": 0.95,
                }
            ],
        }

    monkeypatch.setattr(
        "app.domains.customer_service.services.suggested_actions.CustomerServiceKnowledgeService.search_context",
        fake_search_context,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "AI Reply Metadata Customer",
                        "email": f"{uuid4()}@test.com",
                        "phone": "111",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "chat",
                        "subject": "refund",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "I want a refund. How long does it take?",
                },
            )

            generated = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )
            assert generated.status_code == 200

            reply_action = next(
                action
                for action in generated.json()
                if action["action_type"] == "reply"
            )

            assert reply_action["payload"]["reply_type"] == "refund_review"
            assert (
                reply_action["payload"]["source_summary"]["intent"] == "refund_request"
            )

            accepted = await client.post(
                f"/customer-service/suggested-actions/{reply_action['id']}/accept"
            )
            assert accepted.status_code == 200

            executed = await client.post(
                f"/customer-service/suggested-actions/{reply_action['id']}/execute",
                json={
                    "payload": {
                        "body": reply_action["payload"]["body"],
                    },
                },
            )
            assert executed.status_code == 200, executed.json()

            insights = await client.get(
                "/customer-service/analytics/reply-quality/insights"
            )
            assert insights.status_code == 200

            data = insights.json()

            reply_type_bucket = next(
                bucket
                for bucket in data["by_reply_type"]
                if bucket["key"] == "refund_review"
            )
            intent_bucket = next(
                bucket
                for bucket in data["by_intent"]
                if bucket["key"] == "refund_request"
            )

            assert reply_type_bucket["total"] >= 1
            assert reply_type_bucket["accepted_without_edit"] >= 1
            assert intent_bucket["total"] >= 1
            assert intent_bucket["accepted_without_edit"] >= 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
