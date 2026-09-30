from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-auto-routing@example.com"
        self.customer_service_role = "owner"


async def _create_busy_ticket(client, assignee_id):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Busy Routing Customer",
                "email": f"{uuid4()}@example.com",
                "phone": "+491234",
            },
        )
    ).json()

    await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer["id"],
            "channel": "email",
            "subject": "Busy routing ticket",
        },
    )

    ticket = (await client.get("/customer-service/tickets/")).json()[0]

    assigned = await client.post(
        f"/customer-service/tickets/{ticket['id']}/assign",
        params={"assigned_to": str(assignee_id)},
    )
    assert assigned.status_code == 200


@pytest.mark.asyncio
async def test_omnichannel_inbound_auto_routes_to_least_loaded_policy_candidate():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        assignee_busy = uuid4()
        assignee_free = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await _create_busy_ticket(client, assignee_busy)

            policy = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "WhatsApp shipping routing",
                    "channel": "whatsapp",
                    "intent": "shipping",
                    "priority": "normal",
                    "strategy": "least_loaded",
                    "candidate_assignee_ids": [
                        str(assignee_busy),
                        str(assignee_free),
                    ],
                    "filters": {
                        "keywords": ["order"],
                    },
                },
            )
            assert policy.status_code == 200

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-routing-1",
                    "external_thread_id": "wa-routing-thread-1",
                    "external_message_id": "wa-routing-message-1",
                    "external_customer_id": "wa-routing-customer-1",
                    "customer_name": "Auto Routed Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Where is my order?",
                },
            )

            assert inbound.status_code == 200
            ticket_id = inbound.json()["ticket_id"]

            ticket = await client.get(f"/customer-service/tickets/{ticket_id}")
            assert ticket.status_code == 200
            assert ticket.json()["assigned_to"] == str(assignee_free)

            detail = await client.get(
                f"/customer-service/conversations/{inbound.json()['conversation_id']}"
            )
            assert detail.status_code == 200
            system_messages = [
                message
                for message in detail.json()["messages"]
                if message["sender_type"] == "system"
            ]
            assert any(
                message["meta"]["event"] == "ticket.assigned"
                for message in system_messages
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_omnichannel_inbound_uses_fallback_routing_policy_when_no_exact_match():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        fallback_assignee = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            policy = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "Fallback omnichannel routing",
                    "strategy": "first_available",
                    "candidate_assignee_ids": [str(fallback_assignee)],
                    "priority_rank": 999,
                    "is_fallback": True,
                },
            )
            assert policy.status_code == 200

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "instagram",
                    "external_account_id": "ig-fallback-1",
                    "external_thread_id": "ig-fallback-thread-1",
                    "external_message_id": "ig-fallback-message-1",
                    "external_customer_id": "ig-fallback-customer-1",
                    "customer_name": "Fallback Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Hello, I need help with something unusual",
                },
            )

            assert inbound.status_code == 200
            ticket_id = inbound.json()["ticket_id"]

            ticket = await client.get(f"/customer-service/tickets/{ticket_id}")
            assert ticket.status_code == 200
            assert ticket.json()["assigned_to"] == str(fallback_assignee)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_omnichannel_auto_routing_uses_agent_profile_filters():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        refund_agent = uuid4()
        shipping_agent = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            refund_profile = await client.post(
                "/customer-service/agents",
                json={
                    "agent_user_id": str(refund_agent),
                    "display_name": "Refund Specialist",
                    "skills": ["refunds"],
                    "channels": ["whatsapp"],
                    "languages": ["en"],
                    "max_open_tickets": 10,
                },
            )
            assert refund_profile.status_code == 200

            shipping_profile = await client.post(
                "/customer-service/agents",
                json={
                    "agent_user_id": str(shipping_agent),
                    "display_name": "Shipping Specialist",
                    "skills": ["shipping"],
                    "channels": ["whatsapp"],
                    "languages": ["en"],
                    "max_open_tickets": 10,
                },
            )
            assert shipping_profile.status_code == 200

            policy = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "WhatsApp shipping specialists",
                    "channel": "whatsapp",
                    "intent": "shipping",
                    "priority": "normal",
                    "strategy": "least_loaded",
                    "candidate_assignee_ids": [str(refund_agent), str(shipping_agent)],
                    "filters": {
                        "agent_profile": {
                            "channels": ["whatsapp"],
                            "skills": ["shipping"],
                            "languages": ["en"],
                            "available_only": True,
                            "active_only": True,
                        }
                    },
                },
            )

            assert policy.status_code == 200

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-profile-routing-1",
                    "external_thread_id": "wa-profile-routing-thread-1",
                    "external_message_id": "wa-profile-routing-message-1",
                    "external_customer_id": "wa-profile-routing-customer-1",
                    "customer_name": "Profile Routed Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Where is my shipping package?",
                },
            )

            assert inbound.status_code == 200
            ticket_id = inbound.json()["ticket_id"]

            ticket = await client.get(f"/customer-service/tickets/{ticket_id}")
            assert ticket.status_code == 200
            assert ticket.json()["assigned_to"] == str(shipping_agent)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_omnichannel_auto_routing_uses_team_least_loaded_available_agent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        busy_agent_user_id = uuid4()
        free_agent_user_id = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            busy_agent = await client.post(
                "/customer-service/agents",
                json={
                    "agent_user_id": str(busy_agent_user_id),
                    "display_name": "Busy Team Agent",
                    "skills": ["shipping"],
                    "channels": ["whatsapp"],
                    "languages": ["en"],
                    "max_open_tickets": 10,
                },
            )
            assert busy_agent.status_code == 200

            free_agent = await client.post(
                "/customer-service/agents",
                json={
                    "agent_user_id": str(free_agent_user_id),
                    "display_name": "Free Team Agent",
                    "skills": ["shipping"],
                    "channels": ["whatsapp"],
                    "languages": ["en"],
                    "max_open_tickets": 10,
                },
            )
            assert free_agent.status_code == 200

            team = await client.post(
                "/customer-service/teams",
                json={
                    "name": "WhatsApp Shipping Team",
                    "description": "Routes WhatsApp shipping tickets",
                },
            )
            assert team.status_code == 200
            team_id = team.json()["id"]

            for agent in [busy_agent.json(), free_agent.json()]:
                member = await client.post(
                    f"/customer-service/teams/{team_id}/members",
                    json={"agent_id": agent["id"]},
                )
                assert member.status_code == 200

            await _create_busy_ticket(client, busy_agent_user_id)

            policy = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "WhatsApp team shipping routing",
                    "channel": "whatsapp",
                    "intent": "shipping",
                    "priority": "normal",
                    "strategy": "least_loaded",
                    "candidate_team_ids": [team_id],
                    "filters": {
                        "keywords": ["order"],
                    },
                },
            )
            assert policy.status_code == 200

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-team-routing-1",
                    "external_thread_id": "wa-team-routing-thread-1",
                    "external_message_id": "wa-team-routing-message-1",
                    "external_customer_id": "wa-team-routing-customer-1",
                    "customer_name": "Team Routed Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Where is my order?",
                },
            )
            assert inbound.status_code == 200

            ticket = await client.get(
                f"/customer-service/tickets/{inbound.json()['ticket_id']}"
            )
            assert ticket.status_code == 200
            assert ticket.json()["assigned_to"] == str(free_agent_user_id)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_omnichannel_auto_routing_uses_queue_team_least_loaded_agent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        busy_agent_user_id = uuid4()
        free_agent_user_id = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            busy_agent = await client.post(
                "/customer-service/agents",
                json={
                    "agent_user_id": str(busy_agent_user_id),
                    "display_name": "Busy Queue Agent",
                    "skills": ["shipping"],
                    "channels": ["whatsapp"],
                    "languages": ["en"],
                    "max_open_tickets": 10,
                },
            )
            assert busy_agent.status_code == 200

            free_agent = await client.post(
                "/customer-service/agents",
                json={
                    "agent_user_id": str(free_agent_user_id),
                    "display_name": "Free Queue Agent",
                    "skills": ["shipping"],
                    "channels": ["whatsapp"],
                    "languages": ["en"],
                    "max_open_tickets": 10,
                },
            )
            assert free_agent.status_code == 200

            team = await client.post(
                "/customer-service/teams",
                json={
                    "name": f"Queue Routing Team {uuid4()}",
                    "description": "Owns queue routing",
                },
            )
            assert team.status_code == 200
            team_id = team.json()["id"]

            for agent in [busy_agent.json(), free_agent.json()]:
                member = await client.post(
                    f"/customer-service/teams/{team_id}/members",
                    json={"agent_id": agent["id"]},
                )
                assert member.status_code == 200

            queue = await client.post(
                "/customer-service/queues",
                json={
                    "name": f"WhatsApp Shipping Queue {uuid4()}",
                    "team_id": team_id,
                    "channel": "whatsapp",
                    "intent": "shipping",
                    "priority": "normal",
                    "priority_rank": 10,
                },
            )
            assert queue.status_code == 200

            await _create_busy_ticket(client, busy_agent_user_id)

            policy = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": f"Queue based routing {uuid4()}",
                    "channel": "whatsapp",
                    "intent": "shipping",
                    "priority": "normal",
                    "strategy": "least_loaded",
                    "candidate_queue_ids": [queue.json()["id"]],
                    "filters": {"keywords": ["order"]},
                },
            )
            assert policy.status_code == 200

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-queue-routing-1",
                    "external_thread_id": f"wa-queue-routing-thread-{uuid4()}",
                    "external_message_id": f"wa-queue-routing-message-{uuid4()}",
                    "external_customer_id": f"wa-queue-routing-customer-{uuid4()}",
                    "customer_name": "Queue Routed Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Where is my order?",
                },
            )
            assert inbound.status_code == 200

            ticket = await client.get(
                f"/customer-service/tickets/{inbound.json()['ticket_id']}"
            )
            assert ticket.status_code == 200
            assert ticket.json()["assigned_to"] == str(free_agent_user_id)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
