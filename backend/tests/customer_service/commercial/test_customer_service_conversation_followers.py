from __future__ import annotations

from datetime import datetime, timezone

import asyncio
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update

from app.authentication.service import create_session
from app.core.session import SessionLocal
from app.domains.customer_service.models import ConversationFollower
from app.identity import create_user
from app.main import app
from app.models.models import User as UserORM
from app.models.schemas import UserCreate
from app.tenancy.schemas import (
    WorkspaceCreate,
    WorkspaceInvitationCreate,
)
from app.tenancy.service import WorkspaceService


async def _mark_users_verified(*users) -> None:
    user_ids = [user.id for user in users if user is not None]

    if not user_ids:
        return

    async with SessionLocal() as db:
        await db.execute(
            update(UserORM)
            .where(UserORM.id.in_(user_ids))
            .values(
                email_verified_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()


async def _workspace_with_agent():
    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"followers-owner-{uuid4()}@example.com",
                password=f"Followers-Owner-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        agent = await create_user(
            UserCreate(
                email=f"followers-agent-{uuid4()}@example.com",
                password=f"Followers-Agent-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )

        workspace, _ = await WorkspaceService(db).create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name=f"Followers {uuid4()}"),
        )

        workspace_service = WorkspaceService(db)
        _, token = await workspace_service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(
                email=agent.email,
                role="agent",
            ),
        )

        await workspace_service.accept_invitation(
            token=token,
            user_id=agent.id,
            user_email=agent.email,
        )

    await _mark_users_verified(
        owner,
        agent,
    )

    return owner, agent, workspace


async def _headers(user, workspace):
    async with SessionLocal() as db:
        pair = await create_session(
            db,
            user=user,
            user_agent="pytest-session-fixture",
            ip_address="127.0.0.1",
        )

    return {
        "authorization": f"Bearer {pair.access_token}",
        "x-workspace-id": str(workspace.id),
    }


async def _conversation(client, headers):
    customer = await client.post(
        "/customer-service/customers/",
        json={
            "name": "Follower Customer",
            "email": (f"follower-customer-{uuid4()}@example.com"),
        },
        headers=headers,
    )
    assert customer.status_code == 200, customer.text

    conversation = await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer.json()["id"],
            "channel": "website",
            "subject": "Follower test",
        },
        headers=headers,
    )
    assert conversation.status_code == 200, conversation.text

    return conversation.json()


@pytest.mark.asyncio
async def test_follow_list_unfollow_is_idempotent():
    owner, agent, workspace = await _workspace_with_agent()
    headers = await _headers(owner, workspace)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        conversation = await _conversation(
            client,
            headers,
        )

        url = (
            f"/customer-service/conversations/{conversation['id']}/followers/{agent.id}"
        )

        first = await client.put(
            url,
            headers=headers,
        )
        replay = await client.put(
            url,
            headers=headers,
        )

        assert first.status_code == 200, first.text
        assert replay.status_code == 200, replay.text

        assert replay.json()["id"] == first.json()["id"]
        assert replay.json()["user_id"] == str(agent.id)

        listed = await client.get(
            (f"/customer-service/conversations/{conversation['id']}/followers"),
            headers=headers,
        )

        assert listed.status_code == 200, listed.text
        assert [row["user_id"] for row in listed.json()] == [str(agent.id)]

        removed = await client.delete(
            url,
            headers=headers,
        )
        replay_remove = await client.delete(
            url,
            headers=headers,
        )

        assert removed.status_code == 204
        assert replay_remove.status_code == 204

        listed = await client.get(
            (f"/customer-service/conversations/{conversation['id']}/followers"),
            headers=headers,
        )

        assert listed.status_code == 200
        assert listed.json() == []


@pytest.mark.asyncio
async def test_follow_rejects_non_workspace_member():
    owner, _, workspace = await _workspace_with_agent()
    headers = await _headers(owner, workspace)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        conversation = await _conversation(
            client,
            headers,
        )

        response = await client.put(
            (
                "/customer-service/conversations/"
                f"{conversation['id']}/followers/{uuid4()}"
            ),
            headers=headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == ("Workspace member not found")


@pytest.mark.asyncio
async def test_cross_workspace_conversation_cannot_be_followed():
    owner_a, agent_a, workspace_a = await _workspace_with_agent()
    owner_b, _, workspace_b = await _workspace_with_agent()

    headers_a = await _headers(owner_a, workspace_a)
    headers_b = await _headers(owner_b, workspace_b)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        foreign_conversation = await _conversation(
            client,
            headers_b,
        )

        response = await client.put(
            (
                "/customer-service/conversations/"
                f"{foreign_conversation['id']}"
                f"/followers/{agent_a.id}"
            ),
            headers=headers_a,
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_follow_creates_one_durable_row():
    owner, agent, workspace = await _workspace_with_agent()
    headers = await _headers(owner, workspace)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        conversation = await _conversation(
            client,
            headers,
        )

        url = (
            f"/customer-service/conversations/{conversation['id']}/followers/{agent.id}"
        )

        first, second = await asyncio.gather(
            client.put(url, headers=headers),
            client.put(url, headers=headers),
        )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert first.json()["id"] == second.json()["id"]

        async with SessionLocal() as db:
            count = await db.scalar(
                select(func.count(ConversationFollower.id)).where(
                    ConversationFollower.workspace_id == workspace.id,
                    ConversationFollower.conversation_id == UUID(conversation["id"]),
                    ConversationFollower.user_id == agent.id,
                )
            )

        assert count == 1
