from __future__ import annotations

from uuid import uuid4

import pytest

from httpx import ASGITransport, AsyncClient

from app.main import app

from app.api.auth import get_current_user


class FakeUser:
    id = uuid4()

    email = "unavailable-agent-guards@example.com"
    customer_service_role = "owner"


async def _create_agent(client, *, name, availability="available", skills=None):

    agent_user_id = uuid4()

    response = await client.post(
        "/customer-service/agents",
        json={
            "agent_user_id": str(agent_user_id),
            "display_name": name,
            "email": f"{agent_user_id}@example.com",
            "status": "active",
            "availability": availability,
            "skills": skills or ["refunds"],
            "channels": ["chat"],
            "languages": ["en"],
            "max_open_tickets": 5,
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    data["agent_user_id"] = str(agent_user_id)

    return data


async def _create_team(client):

    response = await client.post(
        "/customer-service/teams",
        json={"name": f"Unavailable Guard Team {uuid4()}"},
    )

    assert response.status_code == 200, response.text

    return response.json()


async def _add_member(client, *, team_id, agent_id):

    response = await client.post(
        f"/customer-service/teams/{team_id}/members",
        json={"agent_id": agent_id},
    )

    assert response.status_code == 200, response.text

    return response.json()


async def _create_customer_conversation(client):

    customer = await client.post(
        "/customer-service/customers/",
        json={
            "name": "Unavailable Routing Customer",
            "email": f"{uuid4()}@example.com",
            "phone": "+491234",
        },
    )

    assert customer.status_code == 200, customer.text

    conversation = await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer.json()["id"],
            "channel": "chat",
            "subject": "Refund help",
        },
    )

    assert conversation.status_code == 200, conversation.text

    return conversation.json()


@pytest.mark.asyncio
async def test_team_routing_skips_unavailable_agent_and_selects_available_agent():

    user = FakeUser()

    user.id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)

            busy = await _create_agent(
                client,
                name="Busy Refund Agent",
                availability="busy",
                skills=["refunds"],
            )

            available = await _create_agent(
                client,
                name="Available Refund Agent",
                availability="available",
                skills=["refunds"],
            )

            await _add_member(client, team_id=team["id"], agent_id=busy["id"])

            await _add_member(client, team_id=team["id"], agent_id=available["id"])

            await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "Skip unavailable team policy",
                    "channel": "chat",
                    "intent": None,
                    "strategy": "least_loaded",
                    "candidate_team_ids": [team["id"]],
                    "filters": {
                        "agent_profile": {
                            "skills": ["refunds"],
                            "channels": ["chat"],
                            "languages": ["en"],
                        }
                    },
                    "priority_rank": 1,
                    "is_fallback": True,
                    "is_active": True,
                },
            )

            conversation = await _create_customer_conversation(client)

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "provider": "generic",
                    "external_account_id": "unavailable-agent-routing",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"msg-{uuid4()}",
                    "channel": "chat",
                    "customer_name": "Unavailable Routing Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "I need a refund please",
                    "direction": "inbound",
                    "conversation_id": conversation["id"],
                    "metadata": {
                        "classification": {"intent": "refund_request"},
                        "action": {"ticket_priority": "normal"},
                    },
                },
            )

            assert inbound.status_code == 200, inbound.text

            ticket_id = inbound.json()["ticket_id"]

            ticket = await client.get(f"/customer-service/tickets/{ticket_id}")

            assert ticket.status_code == 200, ticket.text

            assert ticket.json()["assigned_to"] == available["agent_user_id"]

            assert ticket.json()["assigned_to"] != busy["agent_user_id"]

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_team_routing_returns_unassigned_when_all_agents_unavailable():

    user = FakeUser()

    user.id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)

            away = await _create_agent(
                client,
                name="Away Refund Agent",
                availability="away",
                skills=["refunds"],
            )

            busy = await _create_agent(
                client,
                name="Busy Refund Agent",
                availability="busy",
                skills=["refunds"],
            )

            await _add_member(client, team_id=team["id"], agent_id=away["id"])

            await _add_member(client, team_id=team["id"], agent_id=busy["id"])

            policy = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "All unavailable team policy",
                    "channel": "chat",
                    "intent": None,
                    "strategy": "least_loaded",
                    "candidate_team_ids": [team["id"]],
                    "filters": {
                        "agent_profile": {
                            "skills": ["refunds"],
                            "channels": ["chat"],
                            "languages": ["en"],
                        }
                    },
                    "priority_rank": 1,
                    "is_fallback": True,
                    "is_active": True,
                },
            )

            assert policy.status_code == 200, policy.text

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "provider": "generic",
                    "external_account_id": "all-unavailable-routing",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"msg-{uuid4()}",
                    "channel": "chat",
                    "customer_name": "All Unavailable Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "refund needed",
                    "direction": "inbound",
                    "metadata": {
                        "classification": {"intent": "refund_request"},
                        "action": {"ticket_priority": "normal"},
                    },
                },
            )

            assert inbound.status_code == 200, inbound.text

            ticket_id = inbound.json()["ticket_id"]

            ticket = await client.get(f"/customer-service/tickets/{ticket_id}")

            assert ticket.status_code == 200, ticket.text

            assert ticket.json()["assigned_to"] is None

    finally:
        app.dependency_overrides.clear()
