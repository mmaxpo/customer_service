from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.tenancy.models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
    WorkspaceSettingsAuditLog,
)


class WorkspaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def slug_exists(self, slug: str) -> bool:
        result = await self.db.execute(
            select(Workspace.id).where(Workspace.slug == slug).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_personal_workspace_for_user(
        self,
        *,
        user_id: UUID,
    ) -> Workspace | None:
        result = await self.db.execute(
            select(Workspace).where(
                Workspace.created_by_user_id == user_id,
                Workspace.kind == "personal",
                Workspace.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def create_workspace(
        self,
        *,
        name: str,
        slug: str,
        logo_url: str | None = None,
        support_email: str | None = None,
        default_sender_name: str | None = None,
        default_sender_email: str | None = None,
        default_locale: str = "en",
        timezone: str = "UTC",
        business_hours: dict | None = None,
        kind: str,
        created_by_user_id: UUID,
    ) -> Workspace:
        workspace = Workspace(
            name=name,
            slug=slug,
            logo_url=logo_url,
            support_email=support_email,
            default_sender_name=default_sender_name,
            default_sender_email=default_sender_email,
            default_locale=default_locale,
            timezone=timezone,
            business_hours=business_hours,
            kind=kind,
            status="active",
            created_by_user_id=created_by_user_id,
        )
        self.db.add(workspace)
        await self.db.flush()
        return workspace

    async def get_workspace(self, workspace_id: UUID, *, for_update: bool = False) -> Workspace | None:
        if not for_update:
            return await self.db.get(Workspace, workspace_id)
        result = await self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id: UUID,
    ) -> list[tuple[Workspace, WorkspaceMembership]]:
        result = await self.db.execute(
            select(Workspace, WorkspaceMembership)
            .join(
                WorkspaceMembership,
                WorkspaceMembership.workspace_id == Workspace.id,
            )
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.status == "active",
                Workspace.status == "active",
            )
            .order_by(Workspace.created_at.asc())
        )
        return list(result.tuples().all())

    async def get_membership(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        for_update: bool = False,
    ) -> WorkspaceMembership | None:
        query = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def add_membership(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        role: str,
        invited_by_user_id: UUID | None = None,
    ) -> WorkspaceMembership:
        membership = WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            status="active",
            invited_by_user_id=invited_by_user_id,
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def list_members(
        self,
        *,
        workspace_id: UUID,
    ) -> list[WorkspaceMembership]:
        result = await self.db.execute(
            select(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.status != "removed",
            )
            .order_by(WorkspaceMembership.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_members_with_users(
        self,
        *,
        workspace_id: UUID,
    ) -> list[tuple[WorkspaceMembership, User]]:
        result = await self.db.execute(
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.status != "removed",
            )
            .order_by(WorkspaceMembership.created_at.asc())
        )
        return list(result.tuples().all())

    async def get_membership_by_email(
        self,
        *,
        workspace_id: UUID,
        normalized_email: str,
    ) -> WorkspaceMembership | None:
        result = await self.db.execute(
            select(WorkspaceMembership)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                User.normalized_email == normalized_email,
            )
        )
        return result.scalar_one_or_none()

    async def create_settings_audit_log(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        changes: dict,
    ) -> WorkspaceSettingsAuditLog:
        audit_log = WorkspaceSettingsAuditLog(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action="workspace.settings_updated",
            changes=changes,
        )
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log

    async def create_lifecycle_audit_log(
        self, *, workspace_id: UUID, actor_user_id: UUID, action: str, changes: dict
    ) -> WorkspaceSettingsAuditLog:
        audit_log = WorkspaceSettingsAuditLog(
            workspace_id=workspace_id, actor_user_id=actor_user_id,
            action=action, changes=changes,
        )
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log

    async def list_settings_audit_logs(
        self,
        *,
        workspace_id: UUID,
        limit: int,
        offset: int,
    ) -> list[WorkspaceSettingsAuditLog]:
        result = await self.db.execute(
            select(WorkspaceSettingsAuditLog)
            .where(WorkspaceSettingsAuditLog.workspace_id == workspace_id)
            .order_by(
                WorkspaceSettingsAuditLog.created_at.desc(),
                WorkspaceSettingsAuditLog.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_active_owners(self, *, workspace_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(WorkspaceMembership.id)).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.role == "owner",
                WorkspaceMembership.status == "active",
            )
        )
        return int(result.scalar_one())

    async def lock_active_owner(self, *, workspace_id: UUID) -> WorkspaceMembership | None:
        result = await self.db.execute(
            select(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.role == "owner",
                WorkspaceMembership.status == "active",
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_pending_invitation(
        self,
        *,
        workspace_id: UUID,
        email: str,
    ) -> WorkspaceInvitation | None:
        result = await self.db.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.email == email,
                WorkspaceInvitation.status == "pending",
                WorkspaceInvitation.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def get_invitation_by_hash(
        self,
        *,
        token_hash: str,
        for_update: bool = False,
    ) -> WorkspaceInvitation | None:
        query = select(WorkspaceInvitation).where(
            WorkspaceInvitation.token_hash == token_hash
        )
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_invitation(
        self,
        *,
        workspace_id: UUID,
        email: str,
        role: str,
        token_hash: str,
        invited_by_user_id: UUID,
        expires_at: datetime,
    ) -> WorkspaceInvitation:
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email,
            role=role,
            token_hash=token_hash,
            status="pending",
            invited_by_user_id=invited_by_user_id,
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.flush()
        return invitation

    async def get_invitation(
        self,
        *,
        workspace_id: UUID,
        invitation_id: UUID,
        for_update: bool = False,
    ) -> WorkspaceInvitation | None:
        query = select(WorkspaceInvitation).where(
            WorkspaceInvitation.id == invitation_id,
            WorkspaceInvitation.workspace_id == workspace_id,
        )
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_pending_invitations(
        self,
        *,
        workspace_id: UUID,
    ) -> list[WorkspaceInvitation]:
        result = await self.db.execute(
            select(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.status == "pending",
            )
            .order_by(WorkspaceInvitation.created_at.asc())
        )
        return list(result.scalars().all())


__all__ = ["WorkspaceRepository"]
