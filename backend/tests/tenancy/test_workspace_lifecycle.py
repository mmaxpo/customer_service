from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select

from app.core.session import SessionLocal
from app.identity import create_user
from app.models.models import User
from app.models.schemas import UserCreate
from app.tenancy.models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
    WorkspaceSettingsAuditLog,
)
from app.tenancy.schemas import (
    WorkspaceCreate,
    WorkspaceInvitationCreate,
    WorkspaceMembershipUpdate,
    WorkspaceRole,
    WorkspaceUpdate,
)
from app.tenancy.service import (
    WorkspaceInvitationError,
    WorkspaceInvariantError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
    WorkspaceService,
)
from app.domains.customer_service.models import WorkspaceSubscription


@pytest.mark.asyncio
async def test_workspace_membership_and_invitation_lifecycle():
    suffix = uuid4().hex
    owner_email = f"workspace-owner-{suffix}@example.com"
    agent_email = f"workspace-agent-{suffix}@example.com"
    outsider_email = f"workspace-outsider-{suffix}@example.com"

    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=owner_email,
                password="Correct Horse Battery Staple 1!",
                full_name="Workspace Owner",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        agent = await create_user(
            UserCreate(
                email=agent_email,
                password="Correct Horse Battery Staple 1!",
                full_name="Workspace Agent",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        outsider = await create_user(
            UserCreate(
                email=outsider_email,
                password="Correct Horse Battery Staple 1!",
                full_name="Workspace Outsider",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )

        service = WorkspaceService(db)
        owner_workspaces = await service.list_workspaces(user_id=owner.id)
        assert len(owner_workspaces) == 1
        assert owner_workspaces[0][0].kind == "personal"
        assert owner_workspaces[0][1].role == "owner"

        workspace, owner_membership = await service.create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(
                name="Merchant Operations",
                logo_url="https://cdn.example.test/merchant-logo.svg",
                support_email="support@merchant.example",
                default_sender_name="Merchant Support",
                default_sender_email="help@merchant.example",
                default_locale=" en-US ",
            ),
        )
        assert owner_membership.role == "owner"
        assert workspace.logo_url == "https://cdn.example.test/merchant-logo.svg"
        assert workspace.support_email == "support@merchant.example"
        assert workspace.default_sender_name == "Merchant Support"
        assert workspace.default_sender_email == "help@merchant.example"
        assert workspace.default_locale == "en-US"
        assert workspace.slug == "merchant-operations"

        second_workspace, second_owner_membership = await service.create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name="Merchant Operations"),
        )
        assert second_workspace.id != workspace.id
        assert second_workspace.slug != workspace.slug
        assert second_owner_membership.role == "owner"

        owner_workspaces = await service.list_workspaces(user_id=owner.id)
        assert {row[0].id for row in owner_workspaces} >= {
            workspace.id,
            second_workspace.id,
        }

        with pytest.raises(WorkspaceNotFoundError):
            await service.get_workspace_for_user(
                workspace_id=workspace.id,
                user_id=agent.id,
            )

        with pytest.raises(WorkspaceNotFoundError):
            await service.update_workspace(
                workspace_id=workspace.id,
                user_id=outsider.id,
                payload=WorkspaceUpdate(default_locale="fa"),
            )

        invitation, token = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(
                email=agent_email,
                role=WorkspaceRole.AGENT,
            ),
        )
        assert invitation.token_hash != token
        assert token not in invitation.token_hash

        agent_membership = await service.accept_invitation(
            token=token,
            user_id=agent.id,
            user_email=agent_email,
        )
        assert agent_membership.role == "agent"
        assert agent_membership.status == "active"

        with pytest.raises(WorkspaceInvitationError):
            await service.accept_invitation(
                token=token,
                user_id=agent.id,
                user_email=agent_email,
            )

        with pytest.raises(WorkspacePermissionError):
            await service.update_workspace(
                workspace_id=workspace.id,
                user_id=agent.id,
                payload=WorkspaceUpdate(name="Unauthorized Rename"),
            )

        promoted = await service.update_membership(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            target_user_id=agent.id,
            payload=WorkspaceMembershipUpdate(role=WorkspaceRole.ADMIN),
        )
        assert promoted.role == "admin"

        renamed, _ = await service.update_workspace(
            workspace_id=workspace.id,
            user_id=agent.id,
            payload=WorkspaceUpdate(
                name="Renamed Merchant",
                logo_url="https://cdn.example.test/renamed-logo.svg",
                support_email="new-support@merchant.example",
                default_sender_name=" Merchant Care ",
                default_sender_email="new-help@merchant.example",
                default_locale="fa",
            ),
        )
        assert renamed.name == "Renamed Merchant"
        assert renamed.logo_url == "https://cdn.example.test/renamed-logo.svg"
        assert renamed.support_email == "new-support@merchant.example"
        assert renamed.default_sender_name == "Merchant Care"
        assert renamed.default_sender_email == "new-help@merchant.example"
        assert renamed.default_locale == "fa"

        partially_updated, _ = await service.update_workspace(
            workspace_id=workspace.id,
            user_id=agent.id,
            payload=WorkspaceUpdate(default_sender_name="Aftercare"),
        )
        assert partially_updated.default_sender_name == "Aftercare"
        assert partially_updated.support_email == "new-support@merchant.example"
        assert partially_updated.default_sender_email == "new-help@merchant.example"
        assert partially_updated.default_locale == "fa"

        cleared, _ = await service.update_workspace(
            workspace_id=workspace.id,
            user_id=agent.id,
            payload=WorkspaceUpdate(support_email=None, default_sender_email=None),
        )
        assert cleared.support_email is None
        assert cleared.default_sender_email is None

        with pytest.raises(WorkspaceInvariantError):
            await service.update_membership(
                workspace_id=workspace.id,
                actor_user_id=owner.id,
                target_user_id=owner.id,
                payload=WorkspaceMembershipUpdate(role=WorkspaceRole.ADMIN),
            )

        await db.execute(
            delete(WorkspaceInvitation).where(
                WorkspaceInvitation.workspace_id.in_(
                    [workspace.id, second_workspace.id]
                )
            )
        )
        await db.execute(
            delete(WorkspaceMembership).where(
                WorkspaceMembership.user_id.in_([owner.id, agent.id])
            )
        )
        await db.execute(
            delete(Workspace).where(
                Workspace.created_by_user_id.in_([owner.id, agent.id, outsider.id])
            )
        )
        await db.execute(
            delete(User).where(User.id.in_([owner.id, agent.id, outsider.id]))
        )
        await db.commit()


@pytest.mark.parametrize(
    "payload",
    [
        {"support_email": "not-an-email"},
        {"default_sender_email": "not-an-email"},
        {"name": "   "},
        {"default_sender_name": "   "},
        {"default_locale": "   "},
        {"default_locale": "en_US"},
    ],
)
def test_workspace_profile_update_validation(payload):
    with pytest.raises(ValidationError):
        WorkspaceUpdate(**payload)


@pytest.mark.asyncio
async def test_workspace_settings_changes_are_audited_and_metadata_is_pure_read():
    suffix = uuid4().hex
    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"settings-owner-{suffix}@example.com",
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
                email=f"settings-agent-{suffix}@example.com",
                password="Correct Horse Battery Staple 1!",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        outsider = await create_user(
            UserCreate(
                email=f"settings-outsider-{suffix}@example.com",
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
            payload=WorkspaceCreate(name="Audited Settings Workspace"),
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

        metadata = await service.get_workspace_metadata(
            workspace_id=workspace.id, user_id=owner.id
        )
        assert metadata["workspace_id"] == workspace.id
        assert metadata["created_at"] == workspace.created_at
        assert metadata["plan"] == "trial"
        assert await db.get(WorkspaceSubscription, workspace.id) is None

        db.add(WorkspaceSubscription(workspace_id=workspace.id, plan="pro"))
        await db.commit()
        metadata = await service.get_workspace_metadata(
            workspace_id=workspace.id, user_id=owner.id
        )
        assert metadata["plan"] == "pro"

        await service.update_workspace(
            workspace_id=workspace.id,
            user_id=owner.id,
            payload=WorkspaceUpdate(
                support_email="support@merchant.example",
                default_locale="fa",
                timezone="Asia/Tehran",
                business_hours={
                    "mode": "scheduled",
                    "weekly_hours": {
                        "mon": [{"start": "09:00", "end": "17:00"}],
                    },
                    "holidays": [],
                    "out_of_hours": {
                        "widget_state": "away",
                        "auto_reply_enabled": False,
                        "auto_reply_text": None,
                    },
                },
            ),
        )
        audit_logs = list(
            (
                await db.scalars(
                    select(WorkspaceSettingsAuditLog).where(
                        WorkspaceSettingsAuditLog.workspace_id == workspace.id
                    )
                )
            ).all()
        )
        assert len(audit_logs) == 1
        audit_log = audit_logs[0]
        assert audit_log.actor_user_id == owner.id
        assert audit_log.action == "workspace.settings_updated"
        assert audit_log.created_at is not None
        assert audit_log.changes == {
            "changes": {
                "support_email": {"from": None, "to": "support@merchant.example"},
                "default_locale": {"from": "en", "to": "fa"},
                "timezone": {"from": "UTC", "to": "Asia/Tehran"},
                "business_hours": {
                    "from": None,
                    "to": {
                        "mode": "scheduled",
                        "weekly_hours": {
                            "mon": [{"start": "09:00", "end": "17:00"}],
                        },
                        "holidays": [],
                        "out_of_hours": {
                            "widget_state": "away",
                            "auto_reply_enabled": False,
                            "auto_reply_text": None,
                        },
                    },
                },
            }
        }

        await service.update_workspace(
            workspace_id=workspace.id,
            user_id=owner.id,
            payload=WorkspaceUpdate(default_locale="fa"),
        )
        assert (
            await db.scalar(
                select(func.count(WorkspaceSettingsAuditLog.id)).where(
                    WorkspaceSettingsAuditLog.workspace_id == workspace.id
                )
            )
            == 1
        )

        await service.update_workspace(
            workspace_id=workspace.id,
            user_id=owner.id,
            payload=WorkspaceUpdate(support_email=None),
        )
        audit_logs = await service.list_workspace_settings_audit_logs(
            workspace_id=workspace.id, user_id=owner.id, limit=10, offset=0
        )
        assert len(audit_logs) == 2
        assert audit_logs[0].changes == {
            "changes": {
                "support_email": {"from": "support@merchant.example", "to": None}
            }
        }

        with pytest.raises(WorkspacePermissionError):
            await service.list_workspace_settings_audit_logs(
                workspace_id=workspace.id, user_id=agent.id, limit=10, offset=0
            )
        with pytest.raises(WorkspaceNotFoundError):
            await service.get_workspace_metadata(
                workspace_id=workspace.id, user_id=outsider.id
            )
        with pytest.raises(WorkspaceNotFoundError):
            await service.list_workspace_settings_audit_logs(
                workspace_id=workspace.id, user_id=outsider.id, limit=10, offset=0
            )

        await db.execute(
            delete(Workspace).where(
                Workspace.created_by_user_id.in_([owner.id, agent.id, outsider.id])
            )
        )
        await db.execute(
            delete(User).where(User.id.in_([owner.id, agent.id, outsider.id]))
        )
        await db.commit()


@pytest.mark.asyncio
async def test_membership_removal_revokes_target_sessions():
    from datetime import datetime, timedelta, timezone as dt_timezone

    from app.authentication.models import AuthSession
    from app.tenancy.schemas import MembershipStatus

    suffix = uuid4().hex
    owner_email = f"workspace-owner-{suffix}@example.com"
    agent_email = f"workspace-agent-{suffix}@example.com"

    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=owner_email,
                password="Correct Horse Battery Staple 1!",
                full_name="Workspace Owner",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        agent = await create_user(
            UserCreate(
                email=agent_email,
                password="Correct Horse Battery Staple 1!",
                full_name="Workspace Agent",
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
            payload=WorkspaceCreate(name="Removal Test Workspace"),
        )

        _, token = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(
                email=agent_email,
                role=WorkspaceRole.AGENT,
            ),
        )
        await service.accept_invitation(
            token=token,
            user_id=agent.id,
            user_email=agent_email,
        )

        # Simulate an existing active session for the agent.
        session_row = AuthSession(
            user_id=agent.id,
            family_id=uuid4(),
            refresh_token_hash="test-hash-not-used-for-auth",
            expires_at=datetime.now(dt_timezone.utc) + timedelta(days=1),
        )
        db.add(session_row)
        await db.commit()
        await db.refresh(session_row)
        assert session_row.revoked_at is None

        removed = await service.update_membership(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            target_user_id=agent.id,
            payload=WorkspaceMembershipUpdate(status=MembershipStatus.REMOVED),
        )
        assert removed.status == "removed"

        await db.refresh(session_row)
        assert session_row.revoked_at is not None
        assert session_row.revocation_reason == "workspace_membership_removed"

        await db.execute(
            delete(AuthSession).where(AuthSession.user_id.in_([owner.id, agent.id]))
        )
        await db.execute(
            delete(WorkspaceInvitation).where(
                WorkspaceInvitation.workspace_id == workspace.id
            )
        )
        await db.execute(
            delete(WorkspaceMembership).where(
                WorkspaceMembership.user_id.in_([owner.id, agent.id])
            )
        )
        await db.execute(
            delete(Workspace).where(
                Workspace.created_by_user_id.in_([owner.id, agent.id])
            )
        )
        await db.execute(delete(User).where(User.id.in_([owner.id, agent.id])))
        await db.commit()


@pytest.mark.asyncio
async def test_invitation_resend_revoke_and_team_roster():
    import hashlib
    from datetime import datetime, timedelta, timezone

    from app.tenancy.repository import WorkspaceRepository
    from app.tenancy.schemas import MembershipStatus
    from app.tenancy.service import WorkspaceConflictError, WorkspaceNotFoundError

    suffix = uuid4().hex
    owner_email = f"invite-owner-{suffix}@example.com"
    agent_email = f"invite-agent-{suffix}@example.com"
    revoked_email = f"invite-revoked-{suffix}@example.com"
    suspended_email = f"invite-suspended-{suffix}@example.com"
    removed_email = f"invite-removed-{suffix}@example.com"

    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=owner_email,
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
                email=agent_email,
                password="Correct Horse Battery Staple 1!",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        suspended_user = await create_user(
            UserCreate(
                email=suspended_email,
                password="Correct Horse Battery Staple 1!",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        removed_user = await create_user(
            UserCreate(
                email=removed_email,
                password="Correct Horse Battery Staple 1!",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )

        service = WorkspaceService(db)
        repo = WorkspaceRepository(db)
        workspace, _ = await service.create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name="Invitation Lifecycle Workspace"),
        )

        # --- Resend rotates the token and invalidates the old one ---
        invitation, token_a = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(email=agent_email, role=WorkspaceRole.AGENT),
        )
        original_expiry = invitation.expires_at
        original_token_hash = invitation.token_hash

        resent, token_b = await service.resend_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            invitation_id=invitation.id,
        )
        assert token_b != token_a
        assert resent.token_hash != original_token_hash
        assert resent.status == "pending"
        assert resent.expires_at >= original_expiry

        with pytest.raises(WorkspaceInvitationError):
            await service.accept_invitation(
                token=token_a, user_id=agent.id, user_email=agent_email
            )

        accepted = await service.accept_invitation(
            token=token_b, user_id=agent.id, user_email=agent_email
        )
        assert accepted.role == "agent"
        assert accepted.status == "active"

        # --- Revoke is terminal, idempotent, and blocks acceptance ---
        revoke_invitation, revoke_token = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(email=revoked_email, role=WorkspaceRole.VIEWER),
        )
        revoked = await service.revoke_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            invitation_id=revoke_invitation.id,
        )
        assert revoked.status == "revoked"

        # Idempotent repeat.
        revoked_again = await service.revoke_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            invitation_id=revoke_invitation.id,
        )
        assert revoked_again.status == "revoked"

        with pytest.raises(WorkspaceInvitationError):
            await service.accept_invitation(
                token=revoke_token, user_id=owner.id, user_email=revoked_email
            )

        with pytest.raises(WorkspaceConflictError):
            await service.resend_invitation(
                workspace_id=workspace.id,
                actor_user_id=owner.id,
                invitation_id=revoke_invitation.id,
            )

        # --- Resend/revoke require workspace-scoped lookup ---
        with pytest.raises(WorkspaceNotFoundError):
            await service.resend_invitation(
                workspace_id=workspace.id,
                actor_user_id=owner.id,
                invitation_id=uuid4(),
            )
        with pytest.raises(WorkspaceNotFoundError):
            await service.revoke_invitation(
                workspace_id=workspace.id,
                actor_user_id=owner.id,
                invitation_id=uuid4(),
            )

        # --- Existing active/suspended members cannot be re-invited ---
        with pytest.raises(WorkspaceConflictError):
            await service.create_invitation(
                workspace_id=workspace.id,
                actor_user_id=owner.id,
                payload=WorkspaceInvitationCreate(email=agent_email, role=WorkspaceRole.AGENT),
            )

        suspended_invitation, suspended_token = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(email=suspended_email, role=WorkspaceRole.AGENT),
        )
        await service.accept_invitation(
            token=suspended_token, user_id=suspended_user.id, user_email=suspended_email
        )
        await service.update_membership(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            target_user_id=suspended_user.id,
            payload=WorkspaceMembershipUpdate(status=MembershipStatus.SUSPENDED),
        )
        with pytest.raises(WorkspaceConflictError):
            await service.create_invitation(
                workspace_id=workspace.id,
                actor_user_id=owner.id,
                payload=WorkspaceInvitationCreate(email=suspended_email, role=WorkspaceRole.AGENT),
            )

        # --- Invitation acceptance must not bypass an existing suspension ---
        bypass_token = "bypass-suspended-" + uuid4().hex + uuid4().hex
        await repo.create_invitation(
            workspace_id=workspace.id,
            email=suspended_email,
            role="agent",
            token_hash=hashlib.sha256(bypass_token.encode()).hexdigest(),
            invited_by_user_id=owner.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        await db.commit()
        with pytest.raises(WorkspaceInvitationError):
            await service.accept_invitation(
                token=bypass_token, user_id=suspended_user.id, user_email=suspended_email
            )

        # --- A removed member can be explicitly re-invited and reactivated ---
        removed_invitation, removed_token = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(email=removed_email, role=WorkspaceRole.VIEWER),
        )
        await service.accept_invitation(
            token=removed_token, user_id=removed_user.id, user_email=removed_email
        )
        await service.update_membership(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            target_user_id=removed_user.id,
            payload=WorkspaceMembershipUpdate(status=MembershipStatus.REMOVED),
        )
        rejoin_invitation, rejoin_token = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(email=removed_email, role=WorkspaceRole.AGENT),
        )
        rejoined = await service.accept_invitation(
            token=rejoin_token, user_id=removed_user.id, user_email=removed_email
        )
        assert rejoined.status == "active"
        assert rejoined.role == "agent"

        # --- Team roster composes memberships and pending invitations ---
        pending_invitation, _ = await service.create_invitation(
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            payload=WorkspaceInvitationCreate(
                email=f"invite-pending-{suffix}@example.com", role=WorkspaceRole.VIEWER
            ),
        )
        expired_token = "expired-" + uuid4().hex + uuid4().hex
        expired_invitation = await repo.create_invitation(
            workspace_id=workspace.id,
            email=f"invite-expired-{suffix}@example.com",
            role="agent",
            token_hash=hashlib.sha256(expired_token.encode()).hexdigest(),
            invited_by_user_id=owner.id,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        await db.commit()

        roster = await service.get_team_roster(workspace_id=workspace.id, user_id=owner.id)
        members_by_email = {
            entry["email"]: entry for entry in roster if entry["invitation_id"] is None
        }
        invites_by_email = {
            entry["email"]: entry for entry in roster if entry["invitation_id"] is not None
        }

        assert members_by_email[owner_email]["state"] == "active"
        assert members_by_email[agent_email]["state"] == "active"
        assert members_by_email[suspended_email]["state"] == "deactivated"
        assert members_by_email[removed_email]["state"] == "active"
        assert invites_by_email[pending_invitation.email]["state"] == "pending"
        assert invites_by_email[expired_invitation.email]["state"] == "expired"
        assert revoked_email not in members_by_email
        assert revoked_email not in invites_by_email
        assert all("token" not in entry and "token_hash" not in entry for entry in roster)

        user_ids = [owner.id, agent.id, suspended_user.id, removed_user.id]
        await db.execute(
            delete(WorkspaceInvitation).where(WorkspaceInvitation.workspace_id == workspace.id)
        )
        await db.execute(
            delete(WorkspaceMembership).where(WorkspaceMembership.user_id.in_(user_ids))
        )
        await db.execute(
            delete(Workspace).where(Workspace.created_by_user_id.in_(user_ids))
        )
        await db.execute(delete(User).where(User.id.in_(user_ids)))
        await db.commit()
