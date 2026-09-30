from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.authentication.service import create_session
from app.core.session import SessionLocal
from app.identity import create_user
from app.main import app
from app.models.models import User
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate, WorkspaceInvitationCreate
from app.tenancy.service import WorkspaceService

WORKSPACE_API = Path("app/api/workspaces.py")


def test_workspace_http_adapter_has_no_direct_persistence():
    text = WORKSPACE_API.read_text()
    forbidden = (
        "select(",
        "session.execute(",
        "session.add(",
        "session.commit(",
    )
    assert not [marker for marker in forbidden if marker in text]


async def _authorization(user) -> dict[str, str]:
    async with SessionLocal() as db:
        pair = await create_session(
            db,
            user=user,
            user_agent="pytest-workspace-profile",
            ip_address="127.0.0.1",
        )
    return {"authorization": f"Bearer {pair.access_token}"}


@pytest.mark.asyncio
async def test_workspace_profile_http_read_update_and_authorization():
    suffix = uuid4().hex
    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"profile-owner-{suffix}@example.com",
                password="Correct Horse Battery Staple 1!",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        agent = await create_user(
            UserCreate(
                email=f"profile-agent-{suffix}@example.com",
                password="Correct Horse Battery Staple 1!",
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
            payload=WorkspaceCreate(name="Profile HTTP Workspace"),
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
        await db.execute(
            update(User)
            .where(User.id.in_([owner.id, agent.id]))
            .values(email_verified_at=datetime.now(timezone.utc))
        )
        await db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        metadata_response = await client.get(
            f"/workspaces/{workspace.id}/metadata", headers=await _authorization(owner)
        )
        assert metadata_response.status_code == 200
        assert metadata_response.json() == {
            "workspace_id": str(workspace.id),
            "created_at": metadata_response.json()["created_at"],
            "plan": "trial",
        }

        update_response = await client.patch(
            f"/workspaces/{workspace.id}",
            json={
                "support_email": "support@merchant.example",
                "default_sender_name": "Merchant Care",
                "default_sender_email": "care@merchant.example",
                "default_locale": "fa",
            },
            headers=await _authorization(owner),
        )
        assert update_response.status_code == 200
        assert update_response.json()["default_locale"] == "fa"

        audit_response = await client.get(
            f"/workspaces/{workspace.id}/settings-audit",
            headers=await _authorization(owner),
        )
        assert audit_response.status_code == 200
        assert audit_response.json()[0] | {
            "id": audit_response.json()[0]["id"],
            "created_at": audit_response.json()[0]["created_at"],
        } == {
            "id": audit_response.json()[0]["id"],
            "workspace_id": str(workspace.id),
            "actor_user_id": str(owner.id),
            "action": "workspace.settings_updated",
            "changes": {
                "changes": {
                    "support_email": {"from": None, "to": "support@merchant.example"},
                    "default_sender_name": {"from": None, "to": "Merchant Care"},
                    "default_sender_email": {
                        "from": None,
                        "to": "care@merchant.example",
                    },
                    "default_locale": {"from": "en", "to": "fa"},
                }
            },
            "created_at": audit_response.json()[0]["created_at"],
        }

        read_response = await client.get(
            f"/workspaces/{workspace.id}", headers=await _authorization(owner)
        )
        assert read_response.status_code == 200
        assert read_response.json() | {"role": "owner"} == {
            "id": str(workspace.id),
            "name": "Profile HTTP Workspace",
            "slug": "profile-http-workspace",
            "logo_url": None,
            "support_email": "support@merchant.example",
            "default_sender_name": "Merchant Care",
            "default_sender_email": "care@merchant.example",
            "default_locale": "fa",
            "kind": "organization",
            "status": "active",
            "business_name": None,
            "timezone": None,
            "business_hours": None,
            "created_by_user_id": str(owner.id),
            "created_at": read_response.json()["created_at"],
            "updated_at": read_response.json()["updated_at"],
            "role": "owner",
        }

        forbidden_response = await client.patch(
            f"/workspaces/{workspace.id}",
            json={"default_locale": "de"},
            headers=await _authorization(agent),
        )
        assert forbidden_response.status_code == 403

        forbidden_audit_response = await client.get(
            f"/workspaces/{workspace.id}/settings-audit",
            headers=await _authorization(agent),
        )
        assert forbidden_audit_response.status_code == 403


@pytest.mark.asyncio
async def test_invitation_management_http_authorization_and_tenant_isolation(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.api import workspaces as workspaces_api
    from app.tenancy.schemas import WorkspaceRole

    sent_emails: list[dict] = []

    def fake_send_invitation_email(*, to, workspace_name, role, token, expires_at):
        sent_emails.append(
            {
                "to": to,
                "workspace_name": workspace_name,
                "role": role,
                "token": token,
                "expires_at": expires_at,
            }
        )

    monkeypatch.setattr(
        workspaces_api, "_send_invitation_email", fake_send_invitation_email
    )

    suffix = uuid4().hex

    async def _make_verified_user(label: str):
        async with SessionLocal() as db:
            user = await create_user(
                UserCreate(
                    email=f"{label}-{suffix}@example.com",
                    password="Correct Horse Battery Staple 1!",
                    terms_accepted=True,
                    terms_version="v1",
                    privacy_accepted=True,
                    privacy_version="v1",
                ),
                db,
            )
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(email_verified_at=datetime.now(timezone.utc))
            )
            await db.commit()
        return user

    owner = await _make_verified_user("invite-http-owner")
    admin = await _make_verified_user("invite-http-admin")
    agent_member = await _make_verified_user("invite-http-agent")
    viewer_member = await _make_verified_user("invite-http-viewer")
    outsider_owner = await _make_verified_user("invite-http-outsider")

    async with SessionLocal() as db:
        service = WorkspaceService(db)
        workspace, _ = await service.create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name="Invitation HTTP Workspace"),
        )
        other_workspace, _ = await service.create_workspace(
            user_id=outsider_owner.id,
            payload=WorkspaceCreate(name="Other Tenant Workspace"),
        )

        for user, role in (
            (admin, WorkspaceRole.ADMIN),
            (agent_member, WorkspaceRole.AGENT),
            (viewer_member, WorkspaceRole.VIEWER),
        ):
            _, token = await service.create_invitation(
                workspace_id=workspace.id,
                actor_user_id=owner.id,
                payload=WorkspaceInvitationCreate(email=user.email, role=role),
            )
            await service.accept_invitation(
                token=token, user_id=user.id, user_email=user.email
            )

        other_invitation, _ = await service.create_invitation(
            workspace_id=other_workspace.id,
            actor_user_id=outsider_owner.id,
            payload=WorkspaceInvitationCreate(
                email=f"cross-tenant-target-{suffix}@example.com",
                role=WorkspaceRole.AGENT,
            ),
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            f"/workspaces/{workspace.id}/invitations",
            json={"email": f"new-hire-{suffix}@example.com", "role": "agent"},
            headers=await _authorization(owner),
        )
        assert create_response.status_code == 201
        body = create_response.json()
        assert "token" not in body
        assert "token_hash" not in body
        invitation_id = body["id"]

        assert len(sent_emails) == 1
        assert sent_emails[0]["to"] == f"new-hire-{suffix}@example.com"
        assert sent_emails[0]["workspace_name"] == "Invitation HTTP Workspace"
        assert sent_emails[0]["role"] == "agent"
        created_at = datetime.fromisoformat(body["created_at"])
        expires_at = datetime.fromisoformat(body["expires_at"])
        assert timedelta(hours=167) <= (expires_at - created_at) <= timedelta(hours=169)

        # Agents and viewers cannot manage invitations.
        for forbidden_user in (agent_member, viewer_member):
            forbidden_create = await client.post(
                f"/workspaces/{workspace.id}/invitations",
                json={"email": f"blocked-{suffix}@example.com", "role": "agent"},
                headers=await _authorization(forbidden_user),
            )
            assert forbidden_create.status_code == 403

            forbidden_resend = await client.post(
                f"/workspaces/{workspace.id}/invitations/{invitation_id}/resend",
                headers=await _authorization(forbidden_user),
            )
            assert forbidden_resend.status_code == 403

            forbidden_revoke = await client.post(
                f"/workspaces/{workspace.id}/invitations/{invitation_id}/revoke",
                headers=await _authorization(forbidden_user),
            )
            assert forbidden_revoke.status_code == 403

        # Admins can manage invitations.
        admin_resend = await client.post(
            f"/workspaces/{workspace.id}/invitations/{invitation_id}/resend",
            headers=await _authorization(admin),
        )
        assert admin_resend.status_code == 200
        assert "token" not in admin_resend.json()

        # Cross-tenant isolation: this workspace's admin cannot touch the other tenant's invitation.
        isolation_resend = await client.post(
            f"/workspaces/{workspace.id}/invitations/{other_invitation.id}/resend",
            headers=await _authorization(admin),
        )
        assert isolation_resend.status_code == 404

        isolation_revoke = await client.post(
            f"/workspaces/{workspace.id}/invitations/{other_invitation.id}/revoke",
            headers=await _authorization(admin),
        )
        assert isolation_revoke.status_code == 404

        revoke_response = await client.post(
            f"/workspaces/{workspace.id}/invitations/{invitation_id}/revoke",
            headers=await _authorization(owner),
        )
        assert revoke_response.status_code == 200
        assert revoke_response.json()["status"] == "revoked"

        # Team roster exposes pending/active states without leaking secrets.
        roster_response = await client.get(
            f"/workspaces/{workspace.id}/team",
            headers=await _authorization(owner),
        )
        assert roster_response.status_code == 200
        roster = roster_response.json()
        assert all("token" not in entry and "token_hash" not in entry for entry in roster)
        states_by_email = {entry["email"]: entry["state"] for entry in roster}
        assert states_by_email[owner.email] == "active"
        assert states_by_email[admin.email] == "active"
        assert states_by_email[agent_member.email] == "active"
        assert states_by_email[viewer_member.email] == "active"

        # Viewers can still read the roster (basic team visibility).
        viewer_roster_response = await client.get(
            f"/workspaces/{workspace.id}/team",
            headers=await _authorization(viewer_member),
        )
        assert viewer_roster_response.status_code == 200
