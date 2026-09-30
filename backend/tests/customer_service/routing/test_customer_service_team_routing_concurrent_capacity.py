import asyncio
from collections import Counter
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "team-routing-concurrency@example.com"
        self.customer_service_role = "owner"


async def _create_team(client):
    res = await client.post(
        "/customer-service/teams",
        json={
            "name": "Concurrent Routing Team",
            "description": "Concurrency hardening team",
            "is_active": True,
        },
    )
    assert res.status_code == 200, res.json()
    return res.json()


async def _create_agent(client, *, agent_user_id, display_name):
    res = await client.post(
        "/customer-service/agents",
        json={
            "agent_user_id": str(agent_user_id),
            "display_name": display_name,
            "email": f"{uuid4()}@example.com",
            "status": "active",
            "availability": "available",
            "skills": ["support"],
            "channels": ["whatsapp"],
            "languages": ["en"],
            "max_open_tickets": 1,
        },
    )
    assert res.status_code == 200, res.json()
    return res.json()


async def _add_member(client, *, team_id, agent_id):
    res = await client.post(
        f"/customer-service/teams/{team_id}/members",
        json={"agent_id": agent_id, "role": "member"},
    )
    assert res.status_code == 200, res.json()


@pytest.mark.asyncio
async def test_concurrent_team_routing_respects_agent_capacity():
    """
    Harsh production case:

    Team has two available agents, each max_open_tickets=1.
    Three inbound tickets arrive concurrently.

    Expected:
      - no agent receives more than one open ticket
      - at most two tickets are assigned
      - one ticket remains unassigned when team capacity is exhausted
    """
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        agent_a = uuid4()
        agent_b = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)
            profile_a = await _create_agent(
                client,
                agent_user_id=agent_a,
                display_name="Concurrent Agent A",
            )
            profile_b = await _create_agent(
                client,
                agent_user_id=agent_b,
                display_name="Concurrent Agent B",
            )

            await _add_member(client, team_id=team["id"], agent_id=profile_a["id"])
            await _add_member(client, team_id=team["id"], agent_id=profile_b["id"])

            policy = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "Concurrent team routing policy",
                    "channel": "whatsapp",
                    "intent": None,
                    "priority": None,
                    "strategy": "least_loaded",
                    "candidate_team_ids": [team["id"]],
                    "filters": {
                        "keywords": ["help"],
                        "agent_profile": {
                            "skills": ["support"],
                            "channels": ["whatsapp"],
                            "languages": ["en"],
                            "available_only": True,
                            "active_only": True,
                        },
                    },
                    "priority_rank": 1,
                    "is_fallback": True,
                    "is_active": True,
                },
            )
            assert policy.status_code == 200, policy.json()

        async def inbound_once(index: int):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                res = await client.post(
                    "/customer-service/omnichannel/inbound",
                    json={
                        "channel": "whatsapp",
                        "external_account_id": "team-concurrency-account",
                        "external_thread_id": f"team-concurrency-thread-{index}-{uuid4()}",
                        "external_message_id": f"team-concurrency-message-{index}-{uuid4()}",
                        "external_customer_id": f"team-concurrency-customer-{index}",
                        "customer_name": f"Concurrent Customer {index}",
                        "customer_email": f"{uuid4()}@example.com",
                        "body": "I need help with support",
                    },
                )
                assert res.status_code == 200, res.json()
                ticket_id = res.json()["ticket_id"]
                ticket = await client.get(f"/customer-service/tickets/{ticket_id}")
                assert ticket.status_code == 200, ticket.json()
                return ticket.json()["assigned_to"]

        assigned = await asyncio.gather(
            inbound_once(1),
            inbound_once(2),
            inbound_once(3),
        )

        assigned_non_null = [item for item in assigned if item is not None]
        counts = Counter(assigned_non_null)

        assert len(assigned_non_null) == 2
        assert set(assigned_non_null) == {str(agent_a), str(agent_b)}
        assert all(count == 1 for count in counts.values())
        assert assigned.count(None) == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
