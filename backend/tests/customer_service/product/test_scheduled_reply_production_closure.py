from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update

from app.authentication.service import create_session
from app.core.session import SessionLocal
from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
    process_customer_service_scheduled_reply_job,
)
from app.domains.customer_service.models import (
    ConversationMessage,
    CustomerServiceReplyDraft,
)
from app.domains.customer_service.services.messaging import (
    CustomerServiceMessagingService,
)
from app.identity import create_user
from app.main import app
from app.models.models import User as UserORM
from app.models.models import PlatformJob
from app.models.schemas import UserCreate
from app.platform.jobs.worker import JobWorker
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


async def _mark_users_verified(*users) -> None:
    user_ids = [user.id for user in users if user is not None]

    if not user_ids:
        return

    async with SessionLocal() as db:
        await db.execute(
            update(UserORM)
            .where(UserORM.id.in_(user_ids))
            .values(
                email_verified_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()


async def _merchant():
    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"scheduled-owner-{uuid4()}@example.com",
                password=f"Scheduled-Owner-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )

        workspace, _ = await WorkspaceService(db).create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name=f"Scheduled Reply {uuid4()}"),
        )

    await _mark_users_verified(owner)

    return owner, workspace


async def _headers(user, workspace):
    async with SessionLocal() as db:
        pair = await create_session(
            db,
            user=user,
            user_agent="pytest-session-fixture",
            ip_address="127.0.0.1",
        )

    return {
        "authorization": f"Bearer {pair.access_token}",
        "x-workspace-id": str(workspace.id),
    }


async def _conversation(
    client: AsyncClient,
    headers: dict,
    *,
    channel: str = "website",
):
    customer = await client.post(
        "/customer-service/customers/",
        json={
            "name": "Scheduled Reply Customer",
            "email": (f"scheduled-customer-{uuid4()}@example.com"),
        },
        headers=headers,
    )

    assert customer.status_code == 200, customer.text

    conversation = await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer.json()["id"],
            "channel": channel,
            "subject": "Scheduled reply closure",
        },
        headers=headers,
    )

    assert conversation.status_code == 200, conversation.text

    return customer.json(), conversation.json()


async def _draft(
    client: AsyncClient,
    headers: dict,
    conversation_id: str,
    *,
    body: str = "Send this later.",
):
    response = await client.post(
        (f"/customer-service/conversations/{conversation_id}/drafts"),
        json={
            "body": body,
            "source": "agent",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _scheduled_job(
    *,
    workspace_id,
    draft_id,
    version,
):
    async with SessionLocal() as db:
        return await db.scalar(
            select(PlatformJob).where(
                PlatformJob.user_id == workspace_id,
                PlatformJob.job_type == CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
                PlatformJob.idempotency_key
                == (f"scheduled-reply:{draft_id}:{version}"),
            )
        )


async def _make_job_due(job_id):
    async with SessionLocal() as db:
        job = await db.get(
            PlatformJob,
            job_id,
        )

        assert job is not None

        job.run_after = datetime.now(timezone.utc)

        await db.commit()


@pytest.mark.asyncio
async def test_http_schedule_reschedule_cancel_and_validation_contracts():
    owner, workspace = await _merchant()
    headers = await _headers(owner, workspace)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        _, conversation = await _conversation(
            client,
            headers,
        )

        draft = await _draft(
            client,
            headers,
            conversation["id"],
        )

        assert draft["status"] == "draft"

        initial_version = draft["version"]

        past = await client.post(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            json={
                "scheduled_for": (
                    datetime.now(timezone.utc) - timedelta(minutes=1)
                ).isoformat(),
                "expected_version": (initial_version),
            },
            headers=headers,
        )

        assert past.status_code == 422

        first_time = datetime.now(timezone.utc) + timedelta(hours=1)

        scheduled = await client.post(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            json={
                "scheduled_for": (first_time.isoformat()),
                "expected_version": (initial_version),
            },
            headers=headers,
        )

        assert scheduled.status_code == 200, scheduled.text

        scheduled_body = scheduled.json()

        assert scheduled_body["status"] == "scheduled"
        assert scheduled_body["version"] == initial_version + 1

        first_version = scheduled_body["version"]

        stale = await client.post(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            json={
                "scheduled_for": (first_time + timedelta(hours=1)).isoformat(),
                "expected_version": (initial_version),
            },
            headers=headers,
        )

        assert stale.status_code == 409

        second_time = first_time + timedelta(hours=2)

        rescheduled = await client.post(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            json={
                "scheduled_for": (second_time.isoformat()),
                "expected_version": (first_version),
            },
            headers=headers,
        )

        assert rescheduled.status_code == 200, rescheduled.text

        rescheduled_body = rescheduled.json()

        assert rescheduled_body["status"] == "scheduled"
        assert rescheduled_body["version"] == first_version + 1

        cancelled = await client.delete(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            params={"expected_version": (rescheduled_body["version"])},
            headers=headers,
        )

        assert cancelled.status_code == 200, cancelled.text

        cancelled_body = cancelled.json()

        assert cancelled_body["status"] == "draft"
        assert cancelled_body["scheduled_for"] is None
        assert cancelled_body["scheduled_by_user_id"] is None
        assert cancelled_body["version"] == (rescheduled_body["version"] + 1)


@pytest.mark.asyncio
async def test_foreign_workspace_cannot_schedule_or_cancel_draft():
    owner_a, workspace_a = await _merchant()
    owner_b, workspace_b = await _merchant()

    headers_a = await _headers(
        owner_a,
        workspace_a,
    )
    headers_b = await _headers(
        owner_b,
        workspace_b,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        _, foreign_conversation = await _conversation(
            client,
            headers_b,
        )

        foreign_draft = await _draft(
            client,
            headers_b,
            foreign_conversation["id"],
            body="Foreign workspace draft",
        )

        attack_schedule = await client.post(
            (f"/customer-service/drafts/{foreign_draft['id']}/schedule"),
            json={
                "scheduled_for": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                "expected_version": (foreign_draft["version"]),
            },
            headers=headers_a,
        )

        assert attack_schedule.status_code == 404

        attack_cancel = await client.delete(
            (f"/customer-service/drafts/{foreign_draft['id']}/schedule"),
            params={"expected_version": (foreign_draft["version"])},
            headers=headers_a,
        )

        assert attack_cancel.status_code == 404

    async with SessionLocal() as db:
        persisted = await db.get(
            CustomerServiceReplyDraft,
            UUID(foreign_draft["id"]),
        )

        assert persisted is not None
        assert persisted.workspace_id == workspace_b.id
        assert persisted.status == "draft"


@pytest.mark.asyncio
async def test_real_worker_retry_recovers_sending_exactly_once(
    monkeypatch,
):
    owner, workspace = await _merchant()
    headers = await _headers(owner, workspace)

    original_send_reply = CustomerServiceMessagingService.send_reply

    seen_keys: list[str] = []
    attempts = 0

    async def fail_once_then_send(
        self,
        *,
        workspace_id,
        actor_user_id,
        conversation_id,
        payload,
    ):
        nonlocal attempts

        attempts += 1
        seen_keys.append(payload.idempotency_key)

        if attempts == 1:
            raise RuntimeError("temporary scheduled reply failure")

        return await original_send_reply(
            self,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            conversation_id=conversation_id,
            payload=payload,
        )

    monkeypatch.setattr(
        CustomerServiceMessagingService,
        "send_reply",
        fail_once_then_send,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        _, conversation = await _conversation(
            client,
            headers,
        )

        draft = await _draft(
            client,
            headers,
            conversation["id"],
            body="Retry exactly once.",
        )

        scheduled = await client.post(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            json={
                "scheduled_for": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                "expected_version": (draft["version"]),
            },
            headers=headers,
        )

        assert scheduled.status_code == 200, scheduled.text

        scheduled_body = scheduled.json()

    job = await _scheduled_job(
        workspace_id=workspace.id,
        draft_id=draft["id"],
        version=scheduled_body["version"],
    )

    assert job is not None

    await _make_job_due(job.id)

    async with SessionLocal() as db:
        first = await JobWorker(
            db,
            worker_id=("scheduled-reply-failure-worker"),
        ).run_once(job_id=job.id)

        assert first is not None
        assert first.status == "queued"
        assert first.attempts == 1

        persisted = await db.get(
            CustomerServiceReplyDraft,
            UUID(draft["id"]),
        )

        assert persisted is not None
        assert persisted.status == "sending"
        assert persisted.sent_message_id is None

    # Once the worker has durably claimed the
    # generation, product APIs must not alter it.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        reschedule_while_sending = await client.post(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            json={
                "scheduled_for": (
                    datetime.now(timezone.utc) + timedelta(hours=2)
                ).isoformat(),
                "expected_version": (scheduled_body["version"]),
            },
            headers=headers,
        )

        cancel_while_sending = await client.delete(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            params={"expected_version": (scheduled_body["version"])},
            headers=headers,
        )

        assert reschedule_while_sending.status_code == 409
        assert cancel_while_sending.status_code == 409

    await _make_job_due(job.id)

    async with SessionLocal() as db:
        second = await JobWorker(
            db,
            worker_id=("scheduled-reply-recovery-worker"),
        ).run_once(job_id=job.id)

        assert second is not None
        assert second.status == "succeeded"
        assert second.attempts == 2
        assert second.result["status"] == "sent"

        persisted = await db.get(
            CustomerServiceReplyDraft,
            UUID(draft["id"]),
        )

        assert persisted is not None
        assert persisted.status == "sent"
        assert persisted.sent_message_id is not None

        message_count = await db.scalar(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.conversation_id == UUID(conversation["id"]),
                ConversationMessage.source_type == "commercial_reply",
            )
        )

        assert message_count == 1

    assert attempts == 2

    assert seen_keys == [
        f"reply-draft-{draft['id']}",
        f"reply-draft-{draft['id']}",
    ]


@pytest.mark.asyncio
async def test_email_scheduled_delivery_uses_stable_provider_key_once(
    monkeypatch,
):
    owner, workspace = await _merchant()
    headers = await _headers(owner, workspace)

    provider_calls: list[tuple[tuple, dict]] = []

    def fake_send(*args, **kwargs):
        provider_calls.append((args, kwargs))

        return {"id": "scheduled-email-1"}

    monkeypatch.setattr(
        ("app.domains.customer_service.services.messaging.send_email"),
        fake_send,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        _, conversation = await _conversation(
            client,
            headers,
            channel="email",
        )

        draft = await _draft(
            client,
            headers,
            conversation["id"],
            body="Scheduled email.",
        )

        scheduled = await client.post(
            (f"/customer-service/drafts/{draft['id']}/schedule"),
            json={
                "scheduled_for": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                "expected_version": (draft["version"]),
            },
            headers=headers,
        )

        assert scheduled.status_code == 200, scheduled.text

        scheduled_body = scheduled.json()

    job = await _scheduled_job(
        workspace_id=workspace.id,
        draft_id=draft["id"],
        version=scheduled_body["version"],
    )

    assert job is not None

    await _make_job_due(job.id)

    async with SessionLocal() as db:
        processed = await JobWorker(
            db,
            worker_id=("scheduled-email-worker"),
        ).run_once(job_id=job.id)

        assert processed is not None
        assert processed.status == "succeeded"

        persisted = await db.get(
            CustomerServiceReplyDraft,
            UUID(draft["id"]),
        )

        assert persisted is not None
        assert persisted.status == "sent"

        # Replay the logical handler after the
        # successful worker completion. This must
        # resolve from durable sent state without
        # calling the provider again.
        replay_job = await db.get(
            PlatformJob,
            job.id,
        )

        replay = await process_customer_service_scheduled_reply_job(
            replay_job.payload,
            type(
                "Ctx",
                (),
                {
                    "db": db,
                    "job": replay_job,
                },
            )(),
        )

        assert replay["status"] == "sent"
        assert replay["idempotent_replay"] is True

    assert len(provider_calls) == 1

    _, kwargs = provider_calls[0]

    assert kwargs["idempotency_key"] == f"reply-draft-{draft['id']}"
