from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
    process_customer_service_scheduled_reply_job,
)
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
    CustomerServiceReplyDraft,
    Ticket,
)
from app.domains.customer_service.schemas.helpdesk import (
    ReplyDraftWrite,
)
from app.domains.customer_service.services.helpdesk import (
    CustomerServiceHelpdeskService,
)
from app.models.models import PlatformJob
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


async def helpdesk_context(db):
    user = await create_user(
        UserCreate(
            email=f"helpdesk-{uuid4()}@example.com",
            password=f"Helpdesk-{uuid4()}",
            terms_accepted=True,
            terms_version="v1",
            privacy_accepted=True,
            privacy_version="v1",
        ),
        db,
    )

    workspace, _ = await WorkspaceService(db).create_workspace(
        user_id=user.id,
        payload=WorkspaceCreate(name=f"Helpdesk {uuid4()}"),
    )

    customer = Customer(
        user_id=workspace.id,
        workspace_id=workspace.id,
        name="Store Customer",
        email=f"customer-{uuid4()}@example.com",
    )
    db.add(customer)
    await db.flush()

    conversation = Conversation(
        user_id=workspace.id,
        workspace_id=workspace.id,
        customer_id=customer.id,
        channel="website",
        subject="Help needed",
        status="open",
    )
    db.add(conversation)
    await db.flush()

    db.add(
        Ticket(
            user_id=workspace.id,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            title="Help needed",
            status="open",
            priority="normal",
        )
    )

    await db.commit()

    return (
        user,
        workspace,
        customer,
        conversation,
    )


@pytest.mark.asyncio
async def test_schedule_reschedule_and_old_trigger_is_superseded():
    async with SessionLocal() as db:
        user, workspace, _, conversation = await helpdesk_context(db)

        service = CustomerServiceHelpdeskService(
            db,
            workspace_id=workspace.id,
            actor_user_id=user.id,
        )

        draft = await service.create_draft(
            conversation.id,
            ReplyDraftWrite(body="Send this later."),
        )

        first_time = datetime.now(timezone.utc) + timedelta(hours=1)

        first = await service.schedule_draft(
            draft.id,
            scheduled_for=first_time,
            expected_version=draft.version,
        )

        first_version = first.version

        first_job = await db.scalar(
            select(PlatformJob).where(
                PlatformJob.user_id == workspace.id,
                PlatformJob.job_type == CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
                PlatformJob.idempotency_key
                == (f"scheduled-reply:{draft.id}:{first_version}"),
            )
        )

        assert first_job is not None
        assert first.status == "scheduled"
        assert first.scheduled_for == (first_time)
        assert first.scheduled_by_user_id == user.id

        second_time = first_time + timedelta(hours=1)

        second = await service.schedule_draft(
            draft.id,
            scheduled_for=second_time,
            expected_version=first_version,
        )

        assert second.status == "scheduled"
        assert second.version == (first_version + 1)
        assert second.scheduled_for == (second_time)

        old_trigger = await service.validate_scheduled_draft_trigger(
            draft_id=draft.id,
            expected_version=int(first_job.payload["expected_version"]),
            expected_scheduled_for=str(first_job.payload["expected_scheduled_for"]),
        )

        assert old_trigger["status"] == "superseded"

        second_job = await db.scalar(
            select(PlatformJob).where(
                PlatformJob.user_id == workspace.id,
                PlatformJob.job_type == CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
                PlatformJob.idempotency_key
                == (f"scheduled-reply:{draft.id}:{second.version}"),
            )
        )

        assert second_job is not None

        current_trigger = await service.validate_scheduled_draft_trigger(
            draft_id=draft.id,
            expected_version=int(second_job.payload["expected_version"]),
            expected_scheduled_for=str(second_job.payload["expected_scheduled_for"]),
        )

        assert current_trigger["status"] == "ready"


@pytest.mark.asyncio
async def test_cancel_schedule_makes_old_trigger_superseded():
    async with SessionLocal() as db:
        user, workspace, _, conversation = await helpdesk_context(db)

        service = CustomerServiceHelpdeskService(
            db,
            workspace_id=workspace.id,
            actor_user_id=user.id,
        )

        draft = await service.create_draft(
            conversation.id,
            ReplyDraftWrite(body="Maybe later."),
        )

        scheduled = await service.schedule_draft(
            draft.id,
            scheduled_for=(datetime.now(timezone.utc) + timedelta(hours=1)),
            expected_version=draft.version,
        )

        job = await db.scalar(
            select(PlatformJob).where(
                PlatformJob.user_id == workspace.id,
                PlatformJob.job_type == CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
                PlatformJob.idempotency_key
                == (f"scheduled-reply:{draft.id}:{scheduled.version}"),
            )
        )

        assert job is not None

        scheduled_version = scheduled.version

        cancelled = await service.cancel_scheduled_draft(
            draft.id,
            expected_version=scheduled_version,
        )

        assert cancelled.status == "draft"
        assert cancelled.scheduled_for is None
        assert cancelled.scheduled_by_user_id is None
        assert cancelled.version == (scheduled_version + 1)

        stale = await service.validate_scheduled_draft_trigger(
            draft_id=draft.id,
            expected_version=int(job.payload["expected_version"]),
            expected_scheduled_for=str(job.payload["expected_scheduled_for"]),
        )

        assert stale["status"] == ("superseded")


@pytest.mark.asyncio
async def test_schedule_rejects_past_and_stale_version():
    async with SessionLocal() as db:
        user, workspace, _, conversation = await helpdesk_context(db)

        service = CustomerServiceHelpdeskService(
            db,
            workspace_id=workspace.id,
            actor_user_id=user.id,
        )

        draft = await service.create_draft(
            conversation.id,
            ReplyDraftWrite(body="Version guarded."),
        )

        with pytest.raises(HTTPException) as past:
            await service.schedule_draft(
                draft.id,
                scheduled_for=(datetime.now(timezone.utc) - timedelta(minutes=1)),
                expected_version=draft.version,
            )

        assert past.value.status_code == 422

        scheduled = await service.schedule_draft(
            draft.id,
            scheduled_for=(datetime.now(timezone.utc) + timedelta(hours=1)),
            expected_version=draft.version,
        )

        with pytest.raises(HTTPException) as stale:
            await service.schedule_draft(
                draft.id,
                scheduled_for=(datetime.now(timezone.utc) + timedelta(hours=2)),
                expected_version=(scheduled.version - 1),
            )

        assert stale.value.status_code == 409

        persisted = await db.scalar(
            select(CustomerServiceReplyDraft).where(
                CustomerServiceReplyDraft.id == draft.id
            )
        )

        assert persisted is not None
        assert persisted.version == scheduled.version


@pytest.mark.asyncio
async def test_due_scheduled_job_sends_once_and_marks_draft_sent():
    async with SessionLocal() as db:
        user, workspace, _, conversation = await helpdesk_context(db)

        service = CustomerServiceHelpdeskService(
            db,
            workspace_id=workspace.id,
            actor_user_id=user.id,
        )

        draft = await service.create_draft(
            conversation.id,
            ReplyDraftWrite(body="Scheduled delivery."),
        )

        scheduled = await service.schedule_draft(
            draft.id,
            scheduled_for=(datetime.now(timezone.utc) + timedelta(hours=1)),
            expected_version=draft.version,
        )

        scheduled_version = scheduled.version

        job = await db.scalar(
            select(PlatformJob).where(
                PlatformJob.user_id == workspace.id,
                PlatformJob.job_type == CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
                PlatformJob.idempotency_key
                == (f"scheduled-reply:{draft.id}:{scheduled_version}"),
            )
        )

        assert job is not None

        result = await process_customer_service_scheduled_reply_job(
            job.payload,
            SimpleNamespace(
                db=db,
                job=job,
            ),
        )

        await db.refresh(scheduled)

        assert result["status"] == "sent"
        assert scheduled.status == "sent"
        assert scheduled.sent_message_id is not None
        assert scheduled.version == scheduled_version

        message = await db.scalar(
            select(ConversationMessage).where(
                ConversationMessage.id == scheduled.sent_message_id
            )
        )

        assert message is not None
        assert message.body == ("Scheduled delivery.")
        assert message.source_type == "commercial_reply"
        assert message.meta["delivery"]["status"] == "sent"


@pytest.mark.asyncio
async def test_scheduled_job_replay_does_not_duplicate_message():
    async with SessionLocal() as db:
        user, workspace, _, conversation = await helpdesk_context(db)

        service = CustomerServiceHelpdeskService(
            db,
            workspace_id=workspace.id,
            actor_user_id=user.id,
        )

        draft = await service.create_draft(
            conversation.id,
            ReplyDraftWrite(body="Exactly once."),
        )

        scheduled = await service.schedule_draft(
            draft.id,
            scheduled_for=(datetime.now(timezone.utc) + timedelta(hours=1)),
            expected_version=draft.version,
        )

        job = await db.scalar(
            select(PlatformJob).where(
                PlatformJob.user_id == workspace.id,
                PlatformJob.job_type == CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
                PlatformJob.idempotency_key
                == (f"scheduled-reply:{draft.id}:{scheduled.version}"),
            )
        )

        assert job is not None

        first = await process_customer_service_scheduled_reply_job(
            job.payload,
            SimpleNamespace(
                db=db,
                job=job,
            ),
        )

        second = await process_customer_service_scheduled_reply_job(
            job.payload,
            SimpleNamespace(
                db=db,
                job=job,
            ),
        )

        rows = list(
            (
                await db.scalars(
                    select(ConversationMessage).where(
                        ConversationMessage.conversation_id == conversation.id,
                        ConversationMessage.source_type == "commercial_reply",
                    )
                )
            ).all()
        )

        assert first["status"] == "sent"
        assert second["status"] == "sent"
        assert second["idempotent_replay"] is True
        assert len(rows) == 1
        assert rows[0].id == UUID(first["message_id"])
