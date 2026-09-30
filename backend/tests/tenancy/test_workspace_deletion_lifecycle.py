from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.identity import create_user
from app.models.models import PlatformJob
from app.domains.customer_service.models import CustomerServiceShopifyConnection
from app.models.schemas import UserCreate
from app.platform.jobs.repository import JobRepository
from app.tenancy.models import WorkspaceMembership
from app.tenancy.schemas import WorkspaceCreate, WorkspaceRole
from app.tenancy.service import (
    WORKSPACE_DELETION_PURGE_JOB,
    WorkspaceConflictError,
    WorkspacePermissionError,
    WorkspaceService,
)
from app.tenancy.deletion import WorkspaceDeletionService


async def _user(db, label: str):
    return await create_user(
        UserCreate(
            email=f"{label}-{uuid4().hex}@example.com",
            password="Correct Horse Battery Staple 1!",
            full_name=label,
            terms_accepted=True,
            terms_version="v1",
            privacy_accepted=True,
            privacy_version="v1",
        ),
        db,
    )


@pytest.mark.asyncio
async def test_workspace_deletion_is_owner_confirmed_delayed_and_cancellable():
    async with SessionLocal() as db:
        owner, admin = await _user(db, "deletion-owner"), await _user(db, "deletion-admin")
        service = WorkspaceService(db)
        workspace, _ = await service.create_workspace(
            user_id=owner.id, payload=WorkspaceCreate(name="Deletion Target")
        )
        db.add(WorkspaceMembership(
            workspace_id=workspace.id, user_id=admin.id, role=WorkspaceRole.ADMIN.value,
            status="active",
        ))
        await db.commit()

        with pytest.raises(WorkspacePermissionError):
            await service.request_deletion(
                workspace_id=workspace.id, user_id=admin.id, confirmation=workspace.slug
            )
        with pytest.raises(WorkspaceConflictError):
            await service.request_deletion(
                workspace_id=workspace.id, user_id=owner.id, confirmation="wrong-slug"
            )

        scheduled = await service.request_deletion(
            workspace_id=workspace.id, user_id=owner.id, confirmation=workspace.slug
        )
        assert scheduled.status == "pending_deletion"
        assert scheduled.deletion_requested_at is not None
        assert scheduled.deletion_scheduled_for is not None
        assert scheduled.deletion_requested_by_user_id == owner.id
        with pytest.raises(Exception):  # active-only tenancy is deliberately blocked
            await service.get_workspace_for_user(workspace_id=workspace.id, user_id=owner.id)

        jobs = list((await db.execute(select(PlatformJob).where(
            PlatformJob.job_type == WORKSPACE_DELETION_PURGE_JOB,
            PlatformJob.user_id == workspace.id,
        ))).scalars())
        assert len(jobs) == 1
        job = jobs[0]
        assert job.status == "queued"
        assert job.run_after == scheduled.deletion_scheduled_for
        assert await JobRepository(db).claim_next_due(worker_id="test", job_id=job.id) is None

        again = await service.request_deletion(
            workspace_id=workspace.id, user_id=owner.id, confirmation=workspace.slug
        )
        assert again.deletion_requested_at == scheduled.deletion_requested_at
        assert (await db.scalar(select(func.count(PlatformJob.id)).where(
            PlatformJob.job_type == WORKSPACE_DELETION_PURGE_JOB,
            PlatformJob.user_id == workspace.id,
        ))) == 1

        restored = await service.cancel_deletion(workspace_id=workspace.id, user_id=owner.id)
        assert restored.status == "active"
        assert restored.deletion_requested_at is None
        assert restored.deletion_scheduled_for is None
        # The queued job is intentionally retained, but its original generation
        # cannot destruct a cancellation-restored workspace.
        result = await WorkspaceDeletionService(db).purge(job.payload)
        assert result["status"] == "superseded"
        assert (await service.get_workspace_for_user(workspace_id=workspace.id, user_id=owner.id))[0].status == "active"


@pytest.mark.asyncio
async def test_due_purge_removes_every_shopify_store_credential():
    async with SessionLocal() as db:
        owner = await _user(db, "purge-owner")
        service = WorkspaceService(db)
        workspace, _ = await service.create_workspace(
            user_id=owner.id, payload=WorkspaceCreate(name="Purge Target")
        )
        db.add_all([
            CustomerServiceShopifyConnection(
                user_id=workspace.id, workspace_id=workspace.id,
                shop_domain=f"one-{uuid4().hex}.myshopify.com",
                access_token_encrypted="encrypted-one", status="active",
            ),
            CustomerServiceShopifyConnection(
                user_id=workspace.id, workspace_id=workspace.id,
                shop_domain=f"two-{uuid4().hex}.myshopify.com",
                access_token_encrypted="encrypted-two", status="inactive",
            ),
        ])
        await db.commit()
        scheduled = await service.request_deletion(
            workspace_id=workspace.id, user_id=owner.id, confirmation=workspace.slug
        )
        due = datetime.now(timezone.utc)
        scheduled.deletion_scheduled_for = due
        await db.commit()
        result = await WorkspaceDeletionService(db).purge({
            "workspace_id": str(workspace.id),
            "deletion_requested_at": scheduled.deletion_requested_at.isoformat(),
            "deletion_scheduled_for": due.isoformat(),
        })
        assert result["status"] == "purged"
        assert await db.get(type(workspace), workspace.id) is None
        assert (await db.scalar(select(func.count(CustomerServiceShopifyConnection.id)).where(
            CustomerServiceShopifyConnection.workspace_id == workspace.id
        ))) == 0
