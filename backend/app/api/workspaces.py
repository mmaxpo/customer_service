from __future__ import annotations

import html
from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_verified_user
from app.core.config import settings
from app.core.session import get_db
from app.services.email_service import EmailType, send_email
from app.tenancy.context import Principal, get_current_principal
from app.tenancy.schemas import (
    TeamRosterEntry,
    WorkspaceCreate,
    WorkspaceDeletionRead,
    WorkspaceDeletionRequest,
    WorkspaceInvitationAccept,
    WorkspaceInvitationCreate,
    WorkspaceInvitationRead,
    WorkspaceMembershipRead,
    WorkspaceMembershipUpdate,
    WorkspaceOwnershipTransfer,
    WorkspaceMetadataRead,
    WorkspaceRead,
    WorkspaceUpdate,
    WorkspaceSettingsAuditLogRead,
)
from app.tenancy.service import (
    WorkspaceConflictError,
    WorkspaceError,
    WorkspaceInvariantError,
    WorkspaceInvitationError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
    WorkspaceService,
)
from app.tenancy.usage import WorkspaceUsageService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _send_invitation_email(
    *,
    to: str,
    workspace_name: str,
    role: str,
    token: str,
    expires_at: datetime,
) -> None:
    query = urlencode({"token": token})
    link = f"{settings.WEB_APP_URL.rstrip('/')}/invite/accept?{query}"
    safe_link = html.escape(link, quote=True)
    safe_workspace = html.escape(workspace_name)
    safe_role = html.escape(role)
    expires_label = html.escape(expires_at.strftime("%Y-%m-%d %H:%M UTC"))
    send_email(
        email_type=EmailType.NOREPLY,
        to=to,
        subject=f"You've been invited to join {workspace_name} on Tajeran",
        html=(
            f"<p>You've been invited to join <strong>{safe_workspace}</strong> "
            "on Tajeran.</p>"
            f"<p>Role: {safe_role}</p>"
            f'<p><a href="{safe_link}">Accept invitation</a></p>'
            f"<p>This invitation expires on {expires_label}.</p>"
        ),
    )


def _raise_http(exc: WorkspaceError) -> None:
    if isinstance(exc, WorkspaceNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, WorkspacePermissionError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, (WorkspaceConflictError, WorkspaceInvariantError)):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, WorkspaceInvitationError):
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    raise HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc) or exc.code},
    ) from exc


def _workspace_read(workspace, membership) -> WorkspaceRead:
    # Older workspaces created before working-calendar defaults can carry a
    # null JSON value. Keep the API contract stable while those rows are
    # migrated on their next workspace update.
    values = {
        field: getattr(workspace, field, None)
        for field in WorkspaceRead.model_fields
    }
    values["business_hours"] = values["business_hours"] or {
        "mode": "24_7",
        "weekly_hours": {},
        "holidays": [],
        "out_of_hours": {
            "widget_state": "away",
            "auto_reply_enabled": False,
            "auto_reply_text": None,
        },
    }
    result = WorkspaceRead.model_validate(values)
    return result.model_copy(update={"role": membership.role})


def _deletion_read(workspace) -> WorkspaceDeletionRead:
    return WorkspaceDeletionRead(
        workspace_id=workspace.id,
        status=workspace.status,
        deletion_requested_at=workspace.deletion_requested_at,
        deletion_scheduled_for=workspace.deletion_scheduled_for,
        can_cancel=workspace.status == "pending_deletion",
    )


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    rows = await WorkspaceService(db).list_workspaces(user_id=current_user.id)
    return [_workspace_read(workspace, membership) for workspace, membership in rows]


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    workspace, membership = await WorkspaceService(db).create_workspace(
        user_id=current_user.id,
        payload=payload,
    )
    return _workspace_read(workspace, membership)


@router.get("/current", response_model=WorkspaceRead)
async def get_current_workspace(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    workspace, membership = await WorkspaceService(db).get_workspace_for_user(
        workspace_id=principal.workspace_id,
        user_id=principal.user_id,
    )
    return _workspace_read(workspace, membership)


class ThemeChoice(BaseModel):
    theme: Literal["light", "dark"]


# The signed-in user's light / dark choice. Read and written with plain SQL so
# the User model does not depend on the column (migration ui01) being there.
@router.get("/current/theme")
async def get_theme(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    theme = await db.scalar(
        text('SELECT ui_theme FROM "user" WHERE id = :id'), {"id": principal.user_id}
    )
    return {"theme": theme}


@router.put("/current/theme")
async def set_theme(
    payload: ThemeChoice,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text('UPDATE "user" SET ui_theme = :theme WHERE id = :id'),
        {"theme": payload.theme, "id": principal.user_id},
    )
    await db.commit()
    return {"theme": payload.theme}


@router.get("/current/usage")
async def get_current_workspace_usage(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    if principal.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return await WorkspaceUsageService(db).monthly_summary(
        workspace_id=principal.workspace_id,
    )


@router.get("/current/metadata", response_model=WorkspaceMetadataRead)
async def get_current_workspace_metadata(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await WorkspaceService(db).get_workspace_metadata(
            workspace_id=principal.workspace_id,
            user_id=principal.user_id,
        )
    except WorkspaceError as exc:
        _raise_http(exc)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        workspace, membership = await WorkspaceService(db).get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except WorkspaceError as exc:
        _raise_http(exc)
    return _workspace_read(workspace, membership)


@router.get("/{workspace_id}/metadata", response_model=WorkspaceMetadataRead)
async def get_workspace_metadata(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        return await WorkspaceService(db).get_workspace_metadata(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except WorkspaceError as exc:
        _raise_http(exc)


@router.post("/{workspace_id}/deletion", response_model=WorkspaceDeletionRead)
async def request_workspace_deletion(
    workspace_id: UUID,
    payload: WorkspaceDeletionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        workspace = await WorkspaceService(db).request_deletion(
            workspace_id=workspace_id,
            user_id=current_user.id,
            confirmation=payload.confirmation,
        )
    except WorkspaceError as exc:
        _raise_http(exc)
    return _deletion_read(workspace)


@router.delete("/{workspace_id}/deletion", response_model=WorkspaceDeletionRead)
async def cancel_workspace_deletion(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        workspace = await WorkspaceService(db).cancel_deletion(
            workspace_id=workspace_id, user_id=current_user.id
        )
    except WorkspaceError as exc:
        _raise_http(exc)
    return _deletion_read(workspace)


@router.get(
    "/{workspace_id}/settings-audit",
    response_model=list[WorkspaceSettingsAuditLogRead],
)
async def list_workspace_settings_audit_logs(
    workspace_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        return await WorkspaceService(db).list_workspace_settings_audit_logs(
            workspace_id=workspace_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
    except WorkspaceError as exc:
        _raise_http(exc)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        workspace, membership = await WorkspaceService(db).update_workspace(
            workspace_id=workspace_id,
            user_id=current_user.id,
            payload=payload,
        )
    except WorkspaceError as exc:
        _raise_http(exc)
    return _workspace_read(workspace, membership)


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMembershipRead],
)
async def list_workspace_members(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        return await WorkspaceService(db).list_members(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except WorkspaceError as exc:
        _raise_http(exc)


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMembershipRead,
)
async def update_workspace_membership(
    workspace_id: UUID,
    user_id: UUID,
    payload: WorkspaceMembershipUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        return await WorkspaceService(db).update_membership(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            target_user_id=user_id,
            payload=payload,
        )
    except WorkspaceError as exc:
        _raise_http(exc)


@router.post(
    "/{workspace_id}/ownership-transfer",
    response_model=WorkspaceMembershipRead,
)
async def transfer_workspace_ownership(
    workspace_id: UUID,
    payload: WorkspaceOwnershipTransfer,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        _, new_owner = await WorkspaceService(db).transfer_ownership(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
        return new_owner
    except WorkspaceError as exc:
        _raise_http(exc)


@router.post(
    "/{workspace_id}/invitations",
    response_model=WorkspaceInvitationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_invitation(
    workspace_id: UUID,
    payload: WorkspaceInvitationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        invitation, token = await WorkspaceService(db).create_invitation(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
        workspace, _ = await WorkspaceService(db).get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except WorkspaceError as exc:
        _raise_http(exc)
    background_tasks.add_task(
        _send_invitation_email,
        to=invitation.email,
        workspace_name=workspace.name,
        role=invitation.role,
        token=token,
        expires_at=invitation.expires_at,
    )
    return WorkspaceInvitationRead.model_validate(invitation)


@router.post(
    "/{workspace_id}/invitations/{invitation_id}/resend",
    response_model=WorkspaceInvitationRead,
)
async def resend_workspace_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        invitation, token = await WorkspaceService(db).resend_invitation(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            invitation_id=invitation_id,
        )
        workspace, _ = await WorkspaceService(db).get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except WorkspaceError as exc:
        _raise_http(exc)
    background_tasks.add_task(
        _send_invitation_email,
        to=invitation.email,
        workspace_name=workspace.name,
        role=invitation.role,
        token=token,
        expires_at=invitation.expires_at,
    )
    return WorkspaceInvitationRead.model_validate(invitation)


@router.post(
    "/{workspace_id}/invitations/{invitation_id}/revoke",
    response_model=WorkspaceInvitationRead,
)
async def revoke_workspace_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        invitation = await WorkspaceService(db).revoke_invitation(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            invitation_id=invitation_id,
        )
    except WorkspaceError as exc:
        _raise_http(exc)
    return WorkspaceInvitationRead.model_validate(invitation)


@router.get(
    "/{workspace_id}/team",
    response_model=list[TeamRosterEntry],
)
async def get_workspace_team_roster(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        roster = await WorkspaceService(db).get_team_roster(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except WorkspaceError as exc:
        _raise_http(exc)
    return [TeamRosterEntry.model_validate(entry) for entry in roster]


@router.post(
    "/invitations/accept",
    response_model=WorkspaceMembershipRead,
)
async def accept_workspace_invitation(
    payload: WorkspaceInvitationAccept,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_verified_user),
):
    try:
        return await WorkspaceService(db).accept_invitation(
            token=payload.token,
            user_id=current_user.id,
            user_email=str(current_user.email),
        )
    except WorkspaceError as exc:
        _raise_http(exc)


__all__ = ["router"]
