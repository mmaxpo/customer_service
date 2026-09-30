from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import get_db
from app.domains.customer_service.models import Ticket
from app.domains.customer_service.repositories.agents import (
    CustomerServiceAgentRepository,
)
from app.domains.customer_service.services.workforce.agent_capacity import (
    AgentCapacityService,
)
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.customer_service_role = "owner"


async def _create_agent(client, *, agent_user_id, max_open_tickets=2):
    response = await client.post(
        "/customer-service/agents",
        json={
            "agent_user_id": str(agent_user_id),
            "display_name": "Capacity Agent",
            "email": f"{uuid4()}@example.com",
            "status": "active",
            "availability": "available",
            "skills": ["refunds"],
            "channels": ["chat"],
            "languages": ["en"],
            "max_open_tickets": max_open_tickets,
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


async def _create_conversation_and_ticket(client, *, assigned_to):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Capacity Customer",
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
                "subject": "capacity",
            },
        )
    ).json()

    async for db in get_db():
        ticket = Ticket(
            user_id=app.dependency_overrides[get_current_user]().id,
            conversation_id=conversation["id"],
            title="Capacity ticket",
            status="open",
            priority="normal",
            assigned_to=str(assigned_to),
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)

        return {
            "id": str(ticket.id),
            "conversation_id": str(ticket.conversation_id),
            "assigned_to": ticket.assigned_to,
        }


@pytest.mark.asyncio
async def test_agent_capacity_allows_until_max_open_tickets():
    user = FakeUser()
    agent_user_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created_agent = await _create_agent(
                client,
                agent_user_id=agent_user_id,
                max_open_tickets=2,
            )

            await _create_conversation_and_ticket(
                client,
                assigned_to=agent_user_id,
            )

            async for db in get_db():
                agent = await CustomerServiceAgentRepository(db).get(
                    user_id=user.id,
                    agent_id=created_agent["id"],
                )

                snapshot = await AgentCapacityService(db).capacity_snapshot(
                    user_id=user.id,
                    agent=agent,
                )

                assert snapshot["current_open_tickets"] == 1
                assert snapshot["available_capacity"] == 1
                assert snapshot["can_accept_ticket"] is True

                break

            await _create_conversation_and_ticket(
                client,
                assigned_to=agent_user_id,
            )

            async for db in get_db():
                agent = await CustomerServiceAgentRepository(db).get(
                    user_id=user.id,
                    agent_id=created_agent["id"],
                )

                snapshot = await AgentCapacityService(db).capacity_snapshot(
                    user_id=user.id,
                    agent=agent,
                )

                assert snapshot["current_open_tickets"] == 2
                assert snapshot["available_capacity"] == 0
                assert snapshot["can_accept_ticket"] is False

                break

    finally:
        app.dependency_overrides.pop(get_current_user, None)
