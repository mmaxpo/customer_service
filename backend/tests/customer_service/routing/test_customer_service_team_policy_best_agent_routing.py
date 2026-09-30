from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import get_db
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.tickets import TicketCreate
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.customer_service_role = "owner"


async def _create_team(client):
    response = await client.post(
        "/customer-service/teams",
        json={
            "name": "Refund Routing Team",
            "description": "Refund specialists",
            "is_active": True,
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


async def _create_agent(
    client,
    *,
    display_name,
    agent_user_id,
    skills,
    max_open_tickets=5,
    availability="available",
):
    response = await client.post(
        "/customer-service/agents",
        json={
            "agent_user_id": str(agent_user_id),
            "display_name": display_name,
            "email": f"{uuid4()}@example.com",
            "status": "active",
            "availability": availability,
            "skills": skills,
            "channels": ["chat"],
            "languages": ["en"],
            "max_open_tickets": max_open_tickets,
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


async def _add_member(client, *, team_id, agent_id):
    response = await client.post(
        f"/customer-service/teams/{team_id}/members",
        json={
            "agent_id": agent_id,
            "role": "member",
        },
    )
    assert response.status_code == 200, response.json()


async def _create_customer_conversation(client):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Routing Customer",
                "email": f"{uuid4()}@example.com",
                "phone": "1",
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

    return conversation


async def _create_ticket(*, user_id, conversation_id, assigned_to=None):
    async for db in get_db():
        ticket = await TicketRepository(db).create(
            user_id=user_id,
            ticket=TicketCreate(
                conversation_id=conversation_id,
                title="Refund ticket",
                status="open",
                priority="normal",
                assigned_to=assigned_to,
            ),
        )
        return ticket


async def _add_workload(client, *, user_id, assigned_to):
    conversation = await _create_customer_conversation(client)
    return await _create_ticket(
        user_id=user_id,
        conversation_id=conversation["id"],
        assigned_to=str(assigned_to),
    )


@pytest.mark.asyncio
async def test_routing_policy_team_uses_best_agent_selector():
    user = FakeUser()
    busy_agent_user_id = uuid4()
    free_agent_user_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)

            busy = await _create_agent(
                client,
                display_name="Busy Refund Agent",
                agent_user_id=busy_agent_user_id,
                skills=["refunds"],
            )
            free = await _create_agent(
                client,
                display_name="Free Refund Agent",
                agent_user_id=free_agent_user_id,
                skills=["refunds"],
            )

            await _add_member(client, team_id=team["id"], agent_id=busy["id"])
            await _add_member(client, team_id=team["id"], agent_id=free["id"])

            await _add_workload(
                client,
                user_id=user.id,
                assigned_to=busy_agent_user_id,
            )

            conversation = await _create_customer_conversation(client)
            ticket = await _create_ticket(
                user_id=user.id,
                conversation_id=conversation["id"],
            )

            policy = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "Refund team policy",
                    "channel": "chat",
                    "intent": "refund_request",
                    "priority": None,
                    "strategy": "least_loaded",
                    "candidate_team_ids": [team["id"]],
                    "filters": {
                        "agent_profile": {
                            "skills": ["refunds"],
                            "languages": ["en"],
                        }
                    },
                    "priority_rank": 1,
                    "is_active": True,
                },
            )
            assert policy.status_code == 200, policy.json()

            routed = await client.post(
                f"/customer-service/tickets/{ticket.id}/auto-assign",
                json={
                    "candidate_assignee_ids": [
                        str(busy_agent_user_id),
                        str(free_agent_user_id),
                    ],
                    "strategy": "least_loaded",
                    "reason": "test",
                },
            )

            assert routed.status_code == 200, routed.json()

            refreshed = await client.get(f"/customer-service/tickets/{ticket.id}")
            assert refreshed.status_code == 200, refreshed.json()

            assert refreshed.json()["assigned_to"] == str(free_agent_user_id)

    finally:
        app.dependency_overrides.pop(get_current_user, None)
