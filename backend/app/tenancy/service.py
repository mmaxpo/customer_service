from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import WorkspaceSubscription
from app.identity import normalize_email
from app.tenancy.models import WorkspaceInvitation, WorkspaceMembership, WorkspaceQuota
from app.tenancy.repository import WorkspaceRepository
from app.platform.jobs.service import JobService
from app.authentication.service import revoke_all_user_sessions
from app.tenancy.schemas import (
    DEFAULT_INVITATION_LIFETIME_HOURS,
    MembershipStatus,
    WorkspaceCreate,
    WorkspaceInvitationCreate,
    WorkspaceMembershipUpdate,
    WorkspaceOwnershipTransfer,
    WorkspaceRole,
    WorkspaceUpdate,
)


class WorkspaceError(RuntimeError):
    code = "workspace_error"


class WorkspaceNotFoundError(WorkspaceError):
    code = "workspace_not_found"


class WorkspacePermissionError(WorkspaceError):
    code = "workspace_permission_denied"


class WorkspaceConflictError(WorkspaceError):
    code = "workspace_conflict"


class WorkspaceInvariantError(WorkspaceError):
    code = "workspace_invariant_violation"


class WorkspaceInvitationError(WorkspaceError):
    code = "workspace_invitation_invalid"


WORKSPACE_DELETION_GRACE_PERIOD = timedelta(days=14)
WORKSPACE_DELETION_PURGE_JOB = "workspace.deletion.purge"


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized[:80] or "workspace"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def provision_personal_workspace(
    db: AsyncSession,
    *,
    user_id: UUID,
    email: str,
    full_name: str | None,
) -> None:
    repo = WorkspaceRepository(db)
    existing = await repo.list_for_user(user_id=user_id)
    if existing:
        return

    name_source = (full_name or "").strip() or email.split("@", 1)[0]
    workspace = await repo.create_workspace(
        name=f"{name_source}'s workspace",
        slug=f"personal-{str(user_id).replace('-', '')}",
        kind="personal",
        created_by_user_id=user_id,
    )
    await repo.add_membership(
        workspace_id=workspace.id,
        user_id=user_id,
        role=WorkspaceRole.OWNER.value,
    )
    db.add(WorkspaceQuota(workspace_id=workspace.id))


class WorkspaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WorkspaceRepository(db)

    async def list_workspaces(self, *, user_id: UUID):
        return await self.repo.list_for_user(user_id=user_id)

    async def create_workspace(
        self,
        *,
        user_id: UUID,
        payload: WorkspaceCreate,
    ):
        base_slug = _slugify(payload.slug or payload.name)
        slug = base_slug
        if await self.repo.slug_exists(slug):
            slug = f"{base_slug[:71]}-{uuid4().hex[:8]}"

        workspace = await self.repo.create_workspace(
            name=payload.name,
            slug=slug,
            logo_url=payload.logo_url,
            support_email=(
                str(payload.support_email) if payload.support_email else None
            ),
            default_sender_name=payload.default_sender_name,
            default_sender_email=(
                str(payload.default_sender_email)
                if payload.default_sender_email
                else None
            ),
            default_locale=payload.default_locale,
            timezone=payload.timezone,
            business_hours=payload.business_hours,
            kind="organization",
            created_by_user_id=user_id,
        )
        membership = await self.repo.add_membership(
            workspace_id=workspace.id,
            user_id=user_id,
            role=WorkspaceRole.OWNER.value,
        )
        self.db.add(WorkspaceQuota(workspace_id=workspace.id))
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace, membership

    async def get_workspace_for_user(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ):
        workspace = await self.repo.get_workspace(workspace_id)
        membership = await self.repo.get_membership(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if (
            workspace is None
            or workspace.status != "active"
            or membership is None
            or membership.status != MembershipStatus.ACTIVE.value
        ):
            raise WorkspaceNotFoundError()
        return workspace, membership

    async def request_deletion(
        self, *, workspace_id: UUID, user_id: UUID, confirmation: str
    ):
        workspace = await self.repo.get_workspace(workspace_id, for_update=True)
        membership = await self.repo.get_membership(
            workspace_id=workspace_id, user_id=user_id
        )
        if workspace is None or membership is None or membership.status != MembershipStatus.ACTIVE.value:
            raise WorkspaceNotFoundError()
        self._require_owner(membership)
        if confirmation.strip() != workspace.slug:
            raise WorkspaceConflictError("workspace confirmation does not match slug")
        if workspace.status == "pending_deletion":
            return workspace
        if workspace.status != "active":
            raise WorkspaceConflictError("workspace cannot be scheduled for deletion")

        now = datetime.now(timezone.utc)
        workspace.status = "pending_deletion"
        workspace.deletion_requested_at = now
        workspace.deletion_scheduled_for = now + WORKSPACE_DELETION_GRACE_PERIOD
        workspace.deletion_requested_by_user_id = user_id
        await self.repo.create_lifecycle_audit_log(
            workspace_id=workspace.id, actor_user_id=user_id,
            action="workspace.deletion_requested",
            changes={"scheduled_for": workspace.deletion_scheduled_for.isoformat()},
        )
        await JobService(self.db).enqueue(
            job_type=WORKSPACE_DELETION_PURGE_JOB,
            user_id=workspace.id,
            payload={
                "workspace_id": str(workspace.id),
                "deletion_requested_at": workspace.deletion_requested_at.isoformat(),
                "deletion_scheduled_for": workspace.deletion_scheduled_for.isoformat(),
            },
            run_after=workspace.deletion_scheduled_for,
            idempotency_key=f"workspace-deletion:{workspace.id}:{workspace.deletion_requested_at.isoformat()}",
            commit=False,
        )
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def cancel_deletion(self, *, workspace_id: UUID, user_id: UUID):
        workspace = await self.repo.get_workspace(workspace_id, for_update=True)
        membership = await self.repo.get_membership(
            workspace_id=workspace_id, user_id=user_id
        )
        if workspace is None or membership is None or membership.status != MembershipStatus.ACTIVE.value:
            raise WorkspaceNotFoundError()
        self._require_owner(membership)
        if workspace.status != "pending_deletion":
            raise WorkspaceConflictError("workspace deletion is not cancellable")
        await self.repo.create_lifecycle_audit_log(
            workspace_id=workspace.id, actor_user_id=user_id,
            action="workspace.deletion_cancelled", changes={},
        )
        workspace.status = "active"
        workspace.deletion_requested_at = None
        workspace.deletion_scheduled_for = None
        workspace.deletion_requested_by_user_id = None
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def update_workspace(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        payload: WorkspaceUpdate,
    ):
        workspace, membership = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        self._require_management(membership)
        fields_set = payload.model_fields_set
        values = {
            "name": payload.name,
            "logo_url": payload.logo_url,
            "business_name": payload.business_name,
            "timezone": payload.timezone,
            "business_hours": payload.business_hours,
            "support_email": (
                str(payload.support_email) if payload.support_email else None
            ),
            "default_sender_name": payload.default_sender_name,
            "default_sender_email": (
                str(payload.default_sender_email)
                if payload.default_sender_email
                else None
            ),
            "default_locale": payload.default_locale,
        }
        changes = {}
        for field in fields_set:
            previous = getattr(workspace, field)
            updated = values[field]
            if previous != updated:
                setattr(workspace, field, updated)
                changes[field] = {"from": previous, "to": updated}

        if changes:
            await self.repo.create_settings_audit_log(
                workspace_id=workspace.id,
                actor_user_id=user_id,
                changes={"changes": changes},
            )
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace, membership

    async def get_workspace_metadata(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> dict:
        workspace, _ = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        subscription = await self.db.get(WorkspaceSubscription, workspace.id)
        return {
            "workspace_id": workspace.id,
            "created_at": workspace.created_at,
            # A missing row has the same initial tier as a newly provisioned
            # WorkspaceSubscription, without mutating state on a read.
            "plan": subscription.plan if subscription is not None else "trial",
        }

    async def list_workspace_settings_audit_logs(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        limit: int,
        offset: int,
    ):
        _, membership = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        self._require_management(membership)
        return await self.repo.list_settings_audit_logs(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
        )

    async def list_members(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ):
        _, membership = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        self._require_team_management(membership)
        return await self.repo.list_members(workspace_id=workspace_id)

    async def update_membership(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        target_user_id: UUID,
        payload: WorkspaceMembershipUpdate,
    ) -> WorkspaceMembership:
        _, actor = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=actor_user_id,
        )
        self._require_role_management(actor)

        target = await self.repo.get_membership(
            workspace_id=workspace_id,
            user_id=target_user_id,
            for_update=True,
        )
        if target is None or target.status == MembershipStatus.REMOVED.value:
            raise WorkspaceNotFoundError()

        if target.role == WorkspaceRole.OWNER.value and (
            payload.role is not None
            or (
                payload.status is not None
                and payload.status != MembershipStatus.ACTIVE
            )
        ):
            raise WorkspaceInvariantError(
                "owner membership can only change through ownership transfer"
            )
        if payload.role in {WorkspaceRole.OWNER, WorkspaceRole.VIEWER}:
            raise WorkspacePermissionError(
                "owner and legacy viewer are not assignable ordinary roles"
            )
        if payload.role == WorkspaceRole.ADMIN and actor.role != WorkspaceRole.OWNER.value:
            raise WorkspacePermissionError("only the owner may assign admin")

        old_role = target.role
        if payload.role is not None:
            target.role = payload.role.value
        if payload.status is not None:
            target.status = payload.status.value

        if payload.role is not None and old_role != target.role:
            await self.repo.create_lifecycle_audit_log(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                action="workspace.member_role_changed",
                changes={
                    "target_user_id": str(target_user_id),
                    "from": old_role,
                    "to": target.role,
                },
            )
        await self.db.commit()
        await self.db.refresh(target)

        if payload.status in {MembershipStatus.SUSPENDED, MembershipStatus.REMOVED}:
            await revoke_all_user_sessions(
                self.db,
                user_id=target_user_id,
                reason=f"workspace_membership_{payload.status.value}",
            )

        return target

    async def transfer_ownership(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        payload: WorkspaceOwnershipTransfer,
    ) -> tuple[WorkspaceMembership, WorkspaceMembership]:
        workspace = await self.repo.get_workspace(workspace_id, for_update=True)
        actor = await self.repo.get_membership(
            workspace_id=workspace_id, user_id=actor_user_id, for_update=True
        )
        if (
            workspace is None
            or workspace.status != "active"
            or actor is None
            or actor.status != MembershipStatus.ACTIVE.value
        ):
            raise WorkspaceNotFoundError()
        self._require_owner(actor)
        current_owner = await self.repo.lock_active_owner(workspace_id=workspace_id)
        target = await self.repo.get_membership(
            workspace_id=workspace_id,
            user_id=payload.new_owner_user_id,
            for_update=True,
        )
        if current_owner is None or await self.repo.count_active_owners(workspace_id=workspace_id) != 1:
            raise WorkspaceInvariantError("workspace must have exactly one active owner")
        if target is None or target.status != MembershipStatus.ACTIVE.value:
            raise WorkspaceConflictError("new owner must be an active workspace member")
        if target.id == current_owner.id:
            raise WorkspaceConflictError("new owner is already the owner")

        current_owner.role = WorkspaceRole.ADMIN.value
        target.role = WorkspaceRole.OWNER.value
        await self.repo.create_lifecycle_audit_log(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action="workspace.ownership_transferred",
            changes={
                "from_user_id": str(current_owner.user_id),
                "to_user_id": str(target.user_id),
            },
        )
        await self.db.commit()
        await self.db.refresh(current_owner)
        await self.db.refresh(target)
        return current_owner, target

    async def create_invitation(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        payload: WorkspaceInvitationCreate,
    ):
        _, actor = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=actor_user_id,
        )
        self._require_team_management(actor)
        if payload.role == WorkspaceRole.ADMIN and actor.role != WorkspaceRole.OWNER.value:
            raise WorkspacePermissionError("only the owner may invite an admin")

        email = str(payload.email).strip().lower()
        existing = await self.repo.get_pending_invitation(
            workspace_id=workspace_id,
            email=email,
        )
        if existing is not None:
            raise WorkspaceConflictError("an active invitation already exists")

        existing_member = await self.repo.get_membership_by_email(
            workspace_id=workspace_id,
            normalized_email=normalize_email(email),
        )
        if existing_member is not None:
            if existing_member.status == MembershipStatus.ACTIVE.value:
                raise WorkspaceConflictError("email is already a workspace member")
            if existing_member.status == MembershipStatus.SUSPENDED.value:
                raise WorkspaceConflictError(
                    "member is suspended; reactivate their membership instead of inviting"
                )

        token = secrets.token_urlsafe(48)
        invitation = await self.repo.create_invitation(
            workspace_id=workspace_id,
            email=email,
            role=payload.role.value,
            token_hash=_token_hash(token),
            invited_by_user_id=actor_user_id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=payload.expires_in_hours),
        )
        await self.repo.create_lifecycle_audit_log(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action="workspace.member_invited",
            changes={
                "invitation_id": str(invitation.id),
                "email": email,
                "role": payload.role.value,
            },
        )
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation, token

    async def resend_invitation(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        invitation_id: UUID,
    ) -> tuple[WorkspaceInvitation, str]:
        _, actor = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=actor_user_id,
        )
        self._require_team_management(actor)

        invitation = await self.repo.get_invitation(
            workspace_id=workspace_id,
            invitation_id=invitation_id,
            for_update=True,
        )
        if invitation is None:
            raise WorkspaceNotFoundError()
        if invitation.status == "accepted":
            raise WorkspaceConflictError("invitation has already been accepted")
        if invitation.status == "revoked":
            raise WorkspaceConflictError("invitation has been revoked")

        token = secrets.token_urlsafe(48)
        invitation.token_hash = _token_hash(token)
        invitation.status = "pending"
        invitation.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=DEFAULT_INVITATION_LIFETIME_HOURS
        )
        await self.repo.create_lifecycle_audit_log(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action="workspace.invitation_resent",
            changes={"invitation_id": str(invitation.id), "email": invitation.email},
        )
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation, token

    async def revoke_invitation(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        invitation_id: UUID,
    ) -> WorkspaceInvitation:
        _, actor = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=actor_user_id,
        )
        self._require_team_management(actor)

        invitation = await self.repo.get_invitation(
            workspace_id=workspace_id,
            invitation_id=invitation_id,
            for_update=True,
        )
        if invitation is None:
            raise WorkspaceNotFoundError()
        if invitation.status == "accepted":
            raise WorkspaceConflictError("cannot revoke an accepted invitation")

        if invitation.status != "revoked":
            invitation.status = "revoked"
            await self.repo.create_lifecycle_audit_log(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                action="workspace.invitation_revoked",
                changes={
                    "invitation_id": str(invitation.id),
                    "email": invitation.email,
                },
            )
            await self.db.commit()
            await self.db.refresh(invitation)
        return invitation

    async def get_team_roster(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[dict]:
        _, membership = await self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        self._require_team_management(membership)
        now = datetime.now(timezone.utc)
        entries: list[dict] = []

        for membership, user in await self.repo.list_members_with_users(
            workspace_id=workspace_id
        ):
            if membership.status == MembershipStatus.ACTIVE.value:
                state = "active"
            elif membership.status == MembershipStatus.SUSPENDED.value:
                state = "deactivated"
            else:
                continue
            entries.append(
                {
                    "id": membership.id,
                    "user_id": membership.user_id,
                    "invitation_id": None,
                    "email": user.email,
                    "display_name": user.full_name,
                    "role": membership.role,
                    "state": state,
                    "invited_at": membership.created_at,
                    "joined_at": membership.joined_at,
                }
            )

        for invitation in await self.repo.list_pending_invitations(
            workspace_id=workspace_id
        ):
            expired = invitation.expires_at <= now
            entries.append(
                {
                    "id": invitation.id,
                    "user_id": None,
                    "invitation_id": invitation.id,
                    "email": invitation.email,
                    "display_name": None,
                    "role": invitation.role,
                    "state": "expired" if expired else "pending",
                    "invited_at": invitation.created_at,
                    "joined_at": None,
                }
            )

        return entries

    async def accept_invitation(
        self,
        *,
        token: str,
        user_id: UUID,
        user_email: str,
    ) -> WorkspaceMembership:
        invitation = await self.repo.get_invitation_by_hash(
            token_hash=_token_hash(token),
            for_update=True,
        )
        now = datetime.now(timezone.utc)
        if (
            invitation is None
            or invitation.status != "pending"
            or invitation.expires_at <= now
            or invitation.email != user_email.strip().lower()
        ):
            raise WorkspaceInvitationError()

        membership = await self.repo.get_membership(
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            for_update=True,
        )
        if membership is None:
            membership = await self.repo.add_membership(
                workspace_id=invitation.workspace_id,
                user_id=user_id,
                role=invitation.role,
                invited_by_user_id=invitation.invited_by_user_id,
            )
        elif membership.status == MembershipStatus.SUSPENDED.value:
            raise WorkspaceInvitationError(
                "membership is suspended; contact a workspace admin"
            )
        elif membership.status == MembershipStatus.ACTIVE.value:
            raise WorkspaceInvitationError("already an active workspace member")
        else:
            membership.role = invitation.role
            membership.status = MembershipStatus.ACTIVE.value
            membership.joined_at = now
            membership.invited_by_user_id = invitation.invited_by_user_id

        invitation.status = "accepted"
        invitation.accepted_at = now
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    @staticmethod
    def _require_management(membership: WorkspaceMembership) -> None:
        if membership.role not in {
            WorkspaceRole.OWNER.value,
            WorkspaceRole.ADMIN.value,
        }:
            raise WorkspacePermissionError()

    @staticmethod
    def _require_role_management(membership: WorkspaceMembership) -> None:
        if membership.role not in {
            WorkspaceRole.OWNER.value,
            WorkspaceRole.ADMIN.value,
        }:
            raise WorkspacePermissionError()

    @staticmethod
    def _require_team_management(membership: WorkspaceMembership) -> None:
        if membership.role not in {
            WorkspaceRole.OWNER.value,
            WorkspaceRole.ADMIN.value,
            WorkspaceRole.MANAGER.value,
        }:
            raise WorkspacePermissionError()

    @staticmethod
    def _require_owner(membership: WorkspaceMembership) -> None:
        if membership.role != WorkspaceRole.OWNER.value:
            raise WorkspacePermissionError()


__all__ = [
    "WorkspaceConflictError",
    "WorkspaceError",
    "WorkspaceInvitationError",
    "WorkspaceInvariantError",
    "WorkspaceNotFoundError",
    "WorkspacePermissionError",
    "WorkspaceService",
    "WORKSPACE_DELETION_PURGE_JOB",
    "provision_personal_workspace",
]
