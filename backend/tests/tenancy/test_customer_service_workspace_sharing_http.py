from __future__ import annotations

from datetime import datetime, timezone

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.authentication.service import create_session
from app.core.session import SessionLocal
from app.identity import create_user
from app.main import app
from app.models.models import User as UserORM
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate, WorkspaceInvitationCreate
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


async def _authorization(user) -> dict[str, str]:
    async with SessionLocal() as db:
        pair = await create_session(
            db,
            user=user,
            user_agent="pytest-session-fixture",
            ip_address="127.0.0.1",
        )

    return {
        "authorization": f"Bearer {pair.access_token}",
    }


@pytest.mark.asyncio
async def test_workspace_members_share_customer_service_tenant_data():
    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"merchant-owner-{uuid4()}@example.com",
                password=f"Owner-Password-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        agent = await create_user(
            UserCreate(
                email=f"merchant-agent-{uuid4()}@example.com",
                password=f"Agent-Password-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        outsider = await create_user(
            UserCreate(
                email=f"merchant-outsider-{uuid4()}@example.com",
                password=f"Outsider-Password-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        viewer = await create_user(
            UserCreate(
                email=f"merchant-viewer-{uuid4()}@example.com",
                password=f"Viewer-Password-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        service = WorkspaceService(db)
        workspace, _ = await service.create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name=f"Merchant {uuid4()}"),
        )
        _, invitation_token = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(email=agent.email, role="agent"),
        )
        await service.accept_invitation(
            token=invitation_token,
            user_id=agent.id,
            user_email=agent.email,
        )
        _, viewer_token = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(email=viewer.email, role="viewer"),
        )
        await service.accept_invitation(
            token=viewer_token,
            user_id=viewer.id,
            user_email=viewer.email,
        )

    await _mark_users_verified(
        owner,
        agent,
        outsider,
        viewer,
    )

    workspace_header = {"x-workspace-id": str(workspace.id)}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        created = await client.post(
            "/customer-service/customers/",
            json={"name": "Shared Customer", "email": "shared@example.com"},
            headers={**(await _authorization(owner)), **workspace_header},
        )
        assert created.status_code == 200

        visible = await client.get(
            "/customer-service/customers/",
            headers={**(await _authorization(agent)), **workspace_header},
        )
        assert visible.status_code == 200
        assert [row["email"] for row in visible.json()] == ["shared@example.com"]

        isolated = await client.get(
            "/customer-service/customers/",
            headers={**(await _authorization(outsider)), **workspace_header},
        )
        assert isolated.status_code == 403

        viewer_read = await client.get(
            "/customer-service/customers/",
            headers={**(await _authorization(viewer)), **workspace_header},
        )
        assert viewer_read.status_code == 200
        viewer_write = await client.post(
            "/customer-service/customers/",
            json={"name": "Forbidden", "email": "forbidden@example.com"},
            headers={**(await _authorization(viewer)), **workspace_header},
        )
        assert viewer_write.status_code == 403
