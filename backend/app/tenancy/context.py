from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_verified_user
from app.core.session import get_db
from app.tenancy.models import WorkspaceMembership
from app.tenancy.repository import WorkspaceRepository


@dataclass(frozen=True, slots=True)
class Principal:
    user: Any
    user_id: UUID
    workspace_id: UUID
    membership_id: UUID
    role: str
    selection_source: str


class PrincipalResolver:
    def __init__(self, db: AsyncSession):
        self.repo = WorkspaceRepository(db)

    async def resolve(
        self,
        *,
        user: Any,
        requested_workspace_id: UUID | None,
    ) -> Principal:
        rows = await self.repo.list_for_user(user_id=user.id)
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "workspace_membership_required"},
            )

        selected: tuple[Any, WorkspaceMembership] | None = None
        source = "header"
        if requested_workspace_id is not None:
            selected = next(
                (row for row in rows if row[0].id == requested_workspace_id),
                None,
            )
            if selected is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "workspace_membership_required"},
                )
        else:
            source = "personal_default"
            selected = next(
                (row for row in rows if row[0].kind == "personal"),
                rows[0],
            )

        workspace, membership = selected
        return Principal(
            user=user,
            user_id=user.id,
            workspace_id=workspace.id,
            membership_id=membership.id,
            role=membership.role,
            selection_source=source,
        )


async def get_current_principal(
    x_workspace_id: UUID | None = Header(
        default=None,
        alias="X-Workspace-ID",
    ),
    current_user=Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    return await PrincipalResolver(db).resolve(
        user=current_user,
        requested_workspace_id=x_workspace_id,
    )


__all__ = [
    "Principal",
    "PrincipalResolver",
    "get_current_principal",
]
