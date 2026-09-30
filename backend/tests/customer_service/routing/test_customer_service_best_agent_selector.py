from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import get_db
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.tickets import TicketCreate
from app.domains.customer_service.services.best_agent_selector import (
    BestAgentSelector,
)
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.customer_service_role = "owner"


async def _create_team(client, name="Refund Team"):
    response = await client.post(
        "/customer-service/teams",
        json={
            "name": name,
            "description": "Refund support",
            "is_active": True,
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


async def _create_agent(
    client,
    *,
    display_name,
    skills,
    agent_user_id=None,
    max_open_tickets=5,
    availability="available",
):
    response = await client.post(
        "/customer-service/agents",
        json={
            "agent_user_id": str(agent_user_id or uuid4()),
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
    return response.json()


async def _create_open_ticket_for_agent(client, *, assigned_to):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Workload Customer",
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
                "subject": "workload",
            },
        )
    ).json()

    async for db in get_db():
        ticket = await TicketRepository(db).create(
            user_id=app.dependency_overrides[get_current_user]().id,
            ticket=TicketCreate(
                conversation_id=conversation["id"],
                title="Assigned workload",
                status="open",
                priority="normal",
                assigned_to=str(assigned_to),
            ),
        )

        return {
            "id": str(ticket.id),
            "conversation_id": str(ticket.conversation_id),
            "assigned_to": ticket.assigned_to,
        }


@pytest.mark.asyncio
async def test_best_agent_selector_prefers_lowest_workload_matching_skill():
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
                skills=["refunds"],
                agent_user_id=busy_agent_user_id,
                max_open_tickets=5,
            )
            free = await _create_agent(
                client,
                display_name="Free Refund Agent",
                skills=["refunds"],
                agent_user_id=free_agent_user_id,
                max_open_tickets=5,
            )

            await _add_member(client, team_id=team["id"], agent_id=busy["id"])
            await _add_member(client, team_id=team["id"], agent_id=free["id"])

            await _create_open_ticket_for_agent(
                client,
                assigned_to=busy_agent_user_id,
            )
            await _create_open_ticket_for_agent(
                client,
                assigned_to=busy_agent_user_id,
            )

            async for db in get_db():
                selected = await BestAgentSelector(db).select_for_team(
                    user_id=user.id,
                    team_id=team["id"],
                    required_skills=["refunds"],
                    channel="chat",
                    language="en",
                )

                assert selected is not None
                assert str(selected.agent_user_id) == str(free_agent_user_id)
                break

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_best_agent_selector_skips_unavailable_and_over_capacity_agents():
    user = FakeUser()
    full_agent_user_id = uuid4()
    available_agent_user_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)

            unavailable = await _create_agent(
                client,
                display_name="Unavailable Agent",
                skills=["refunds"],
                availability="busy",
            )
            full = await _create_agent(
                client,
                display_name="Full Agent",
                skills=["refunds"],
                agent_user_id=full_agent_user_id,
                max_open_tickets=1,
            )
            available = await _create_agent(
                client,
                display_name="Available Agent",
                skills=["refunds"],
                agent_user_id=available_agent_user_id,
                max_open_tickets=3,
            )

            await _add_member(client, team_id=team["id"], agent_id=unavailable["id"])
            await _add_member(client, team_id=team["id"], agent_id=full["id"])
            await _add_member(client, team_id=team["id"], agent_id=available["id"])

            await _create_open_ticket_for_agent(
                client,
                assigned_to=full_agent_user_id,
            )

            async for db in get_db():
                selected = await BestAgentSelector(db).select_for_team(
                    user_id=user.id,
                    team_id=team["id"],
                    required_skills=["refunds"],
                    channel="chat",
                    language="en",
                )

                assert selected is not None
                assert str(selected.agent_user_id) == str(available_agent_user_id)
                break

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_best_agent_selector_returns_none_when_no_skill_match():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)

            shipping_agent = await _create_agent(
                client,
                display_name="Shipping Agent",
                skills=["shipping"],
            )

            await _add_member(
                client,
                team_id=team["id"],
                agent_id=shipping_agent["id"],
            )

            async for db in get_db():
                selected = await BestAgentSelector(db).select_for_team(
                    user_id=user.id,
                    team_id=team["id"],
                    required_skills=["refunds"],
                )

                assert selected is None
                break

    finally:
        app.dependency_overrides.pop(get_current_user, None)
