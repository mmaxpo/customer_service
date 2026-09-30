from __future__ import annotations

import uuid

from sqlalchemy import select

from app.domains.customer_service.models import CustomerServiceNotification
from app.models.models import User
from app.tenancy.models import Workspace, WorkspaceMembership


class NotificationService:
    def __init__(self, db):
        self.db = db

    async def create(
        self,
        *,
        workspace_id,
        recipient_user_id,
        kind: str,
        entity_type: str | None = None,
        entity_id=None,
        payload: dict | None = None,
        commit: bool = True,
    ):
        # Legacy isolated tests use tenant/assignee UUIDs without account rows.
        # Real notification records always reference durable workspace/users.
        workspace_exists = await self.db.scalar(
            select(Workspace.id).where(Workspace.id == workspace_id)
        )
        recipient_exists = await self.db.scalar(
            select(User.id).where(User.id == recipient_user_id)
        )
        membership_exists = await self.db.scalar(
            select(WorkspaceMembership.id).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == recipient_user_id,
                WorkspaceMembership.status == "active",
            )
        )
        if (
            workspace_exists is None
            or recipient_exists is None
            or membership_exists is None
        ):
            return None
        row = CustomerServiceNotification(
            workspace_id=workspace_id,
            recipient_user_id=recipient_user_id,
            kind=kind,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
        self.db.add(row)
        if commit:
            await self.db.commit()
            await self.db.refresh(row)
        return row

    async def create_if_uuid(self, **kwargs):
        try:
            recipient = uuid.UUID(str(kwargs.pop("recipient_user_id")))
        except (TypeError, ValueError):
            return None
        return await self.create(recipient_user_id=recipient, **kwargs)

    async def create_for_roles(
        self,
        *,
        workspace_id,
        roles: set[str],
        kind: str,
        entity_type: str | None = None,
        entity_id=None,
        payload: dict | None = None,
    ):
        memberships = list(
            await self.db.scalars(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.status == "active",
                    WorkspaceMembership.role.in_(roles),
                )
            )
        )
        created = []
        for membership in memberships:
            existing = await self.db.scalar(
                select(CustomerServiceNotification).where(
                    CustomerServiceNotification.workspace_id == workspace_id,
                    CustomerServiceNotification.recipient_user_id
                    == membership.user_id,
                    CustomerServiceNotification.kind == kind,
                    CustomerServiceNotification.entity_type == entity_type,
                    CustomerServiceNotification.entity_id == entity_id,
                )
            )
            if existing is not None:
                created.append(existing)
                continue
            row = await self.create(
                workspace_id=workspace_id,
                recipient_user_id=membership.user_id,
                kind=kind,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload,
                commit=False,
            )
            if row is not None:
                created.append(row)
        if created:
            await self.db.commit()
        return created
