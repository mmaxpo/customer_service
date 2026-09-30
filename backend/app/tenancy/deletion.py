"""Irreversible, delayed workspace deletion handler.

The grace-period APIs intentionally retain credentials.  This module is the
single place that transitions a due request into irreversible destruction.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceAttachment
from app.domains.customer_service.models import WorkspaceSubscription
from app.domains.customer_service.repositories.shopify import ShopifyRepository
from app.domains.customer_service.services.attachment_storage import AttachmentStorage
from app.models import Base
from app.tenancy.repository import WorkspaceRepository


WORKSPACE_DELETION_PURGE_JOB = "workspace.deletion.purge"


def _payload_datetime(payload: dict, field: str) -> datetime:
    value = payload.get(field)
    if not value:
        raise ValueError(f"{field} is required")
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class WorkspaceDeletionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.workspaces = WorkspaceRepository(db)

    async def purge(self, payload: dict) -> dict:
        workspace_id = UUID(str(payload["workspace_id"]))
        requested_at = _payload_datetime(payload, "deletion_requested_at")
        scheduled_for = _payload_datetime(payload, "deletion_scheduled_for")
        workspace = await self.workspaces.get_workspace(workspace_id, for_update=True)
        if workspace is None:
            return {"status": "already_deleted", "workspace_id": str(workspace_id)}

        now = datetime.now(timezone.utc)
        if (
            workspace.status != "pending_deletion"
            or workspace.deletion_requested_at != requested_at
            or workspace.deletion_scheduled_for != scheduled_for
        ):
            # A cancelled request (or a newer request generation) must never
            # be revived by an old queued job.
            return {"status": "superseded", "workspace_id": str(workspace_id)}
        if scheduled_for > now:
            # The worker normally cannot claim this job early; retain this
            # guard for direct/manual invocations.
            return {"status": "not_due", "workspace_id": str(workspace_id)}

        workspace.status = "purging"
        actor_id = workspace.deletion_requested_by_user_id
        if actor_id is not None:
            await self.workspaces.create_lifecycle_audit_log(
                workspace_id=workspace.id,
                actor_user_id=actor_id,
                action="workspace.deletion_purge_started",
                changes={},
            )
        await self.db.flush()

        await self._destroy_shopify_credentials(workspace.id, now)
        subscription = await self.db.get(WorkspaceSubscription, workspace.id)
        if subscription is not None:
            # The current billing integration is webhook-backed and exposes
            # no provider cancellation primitive.  Mark local billing
            # terminal before the workspace row is removed.
            subscription.status = "canceled"
            subscription.cancel_at_period_end = True
            await self.db.flush()
        await self._delete_attachment_objects(workspace.id)
        await self._delete_workspace_rows(workspace.id)
        await self.db.delete(workspace)
        await self.db.flush()
        return {"status": "purged", "workspace_id": str(workspace_id)}

    async def _destroy_shopify_credentials(self, workspace_id: UUID, now: datetime) -> None:
        # No supported remote revoke/uninstall primitive exists in the current
        # provider abstraction.  Local encrypted credentials are therefore
        # destroyed deterministically for every store, active or not.
        for connection in await ShopifyRepository(self.db).list_connections_for_workspace(
            workspace_id=workspace_id
        ):
            connection.access_token_encrypted = None
            connection.status = "inactive"
            connection.revoked_at = now
            connection.reauth_required_at = None
        await self.db.flush()

    async def _delete_attachment_objects(self, workspace_id: UUID) -> None:
        keys = list((await self.db.execute(
            select(CustomerServiceAttachment.storage_key).where(
                CustomerServiceAttachment.workspace_id == workspace_id
            )
        )).scalars())
        storage = AttachmentStorage()
        for key in keys:
            await storage.delete(key=key)

    async def _delete_workspace_rows(self, workspace_id: UUID) -> None:
        """Delete direct workspace-owned rows leaves-first.

        All mapped workspace tables are considered, avoiding a brittle list of
        product tables.  Rows are restricted by their own ``workspace_id``;
        no user/global row can be selected by this operation.  SQLAlchemy's
        dependency ordering gives child tables precedence over their parents.
        """
        for table in reversed(Base.metadata.sorted_tables):
            if table.name == "workspaces" or "workspace_id" not in table.c:
                continue
            await self.db.execute(delete(table).where(table.c.workspace_id == workspace_id))


async def purge_workspace_deletion_job(payload: dict, ctx) -> dict:
    return await WorkspaceDeletionService(ctx.db).purge(payload)


def register_workspace_deletion_job_handlers(registry) -> None:
    registry.register(WORKSPACE_DELETION_PURGE_JOB, purge_workspace_deletion_job)


__all__ = [
    "WORKSPACE_DELETION_PURGE_JOB",
    "WorkspaceDeletionService",
    "purge_workspace_deletion_job",
    "register_workspace_deletion_job_handlers",
]
