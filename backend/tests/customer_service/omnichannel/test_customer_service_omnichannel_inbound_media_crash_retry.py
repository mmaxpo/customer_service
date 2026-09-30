from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.session import SessionLocal
from app.domains.customer_service.integrations.omnichannel.protocol import (
    FetchedInboundMedia,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
    CustomerServiceAttachment,
    CustomerServiceExternalMediaLink,
    MessageSenderType,
)
from app.domains.customer_service.repositories.omnichannel import (
    OmnichannelRepository,
)
from app.domains.customer_service.workflows.omnichannel_job_types import (
    OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
)
from app.identity import create_user
from app.models.schemas import UserCreate
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


@pytest.mark.asyncio
async def test_media_link_failure_rolls_back_db_and_retry_reuses_storage(
    monkeypatch,
):
    """
    Production crash-window attack:

    attempt 1:
        provider fetch succeeds
        physical storage succeeds
        attachment row flushes
        external-media link fails

    expected:
        attachment DB row rolls back
        job is queued for retry

    attempt 2:
        deterministic attachment id/storage key reused
        exactly one attachment + one link become durable
    """

    from app.domains.customer_service.workflows import (
        omnichannel_jobs as jobs_module,
    )

    conversation_id = uuid4()
    message_id = uuid4()

    channel = f"media-crash-{uuid4().hex}"
    external_account_id = "account-1"
    external_thread_id = "thread-1"
    external_message_id = "message-1"
    provider_media_id = "media-1"

    fetch_calls = 0
    link_calls = 0

    class CrashRetryProvider:
        def __init__(self):
            self.channel = channel

        async def fetch_media(
            self,
            *,
            media,
            connection,
        ):
            nonlocal fetch_calls

            fetch_calls += 1

            assert media.provider_media_id == provider_media_id

            assert connection.external_account_id == external_account_id

            return FetchedInboundMedia(
                content=b"crash-retry-media",
                filename="crash-retry.jpg",
                content_type="image/jpeg",
                metadata={
                    "attempt": fetch_calls,
                },
            )

    registry = get_omnichannel_provider_registry()

    test_adapters = dict(registry._adapters)
    test_adapters[channel] = CrashRetryProvider()
    monkeypatch.setattr(registry, "_adapters", test_adapters)

    original_link = OmnichannelRepository.link_external_media

    async def fail_first_link(
        self,
        **kwargs,
    ):
        nonlocal link_calls

        link_calls += 1

        if link_calls == 1:
            raise RuntimeError("injected failure after attachment storage")

        return await original_link(
            self,
            **kwargs,
        )

    monkeypatch.setattr(
        OmnichannelRepository,
        "link_external_media",
        fail_first_link,
    )

    # Do not overwrite our test provider with defaults.
    monkeypatch.setattr(
        jobs_module,
        "register_default_omnichannel_providers",
        lambda: None,
    )

    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"media-crash-{uuid4()}@example.com",
                password=f"Media-Crash-{uuid4()}",
            ),
            db,
        )

        workspace, _ = await WorkspaceService(db).create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name=f"Media Crash {uuid4()}"),
        )

        # Customer Service uses the workspace identity as its
        # tenant/user_id boundary.
        user_id = workspace.id

        payload = {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id),
            "message_id": str(message_id),
            "channel": channel,
            "external_account_id": external_account_id,
            "external_message_id": external_message_id,
            "provider_media_id": provider_media_id,
            "media": {
                "provider_media_id": provider_media_id,
                "filename": "source.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 17,
                "metadata": {},
            },
        }

        customer = Customer(
            user_id=user_id,
            workspace_id=user_id,
            name="Crash Retry Customer",
        )
        db.add(customer)
        await db.flush()

        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            workspace_id=user_id,
            customer_id=customer.id,
            channel=channel,
            subject="Inbound media crash retry",
            status="open",
        )
        db.add(conversation)

        message = ConversationMessage(
            id=message_id,
            conversation_id=conversation_id,
            sender_type=MessageSenderType.CUSTOMER,
            body="",
        )
        db.add(message)

        await db.flush()

        attachment_id = uuid5(
            NAMESPACE_URL,
            (
                "customer-service:external-media:"
                f"{user_id}:"
                f"{channel}:"
                f"{external_account_id}:"
                f"{external_message_id}:"
                f"{provider_media_id}"
            ),
        )

        storage_key = f"{user_id}/{attachment_id.hex}.bin"

        storage_path = Path(settings.ATTACHMENT_STORAGE_ROOT) / storage_key

        repo = OmnichannelRepository(db)

        connection = await repo.create_connection(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            config={},
        )

        assert connection is not None

        await repo.link_external_message(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            channel=channel,
            external_account_id=external_account_id,
            external_thread_id=external_thread_id,
            external_message_id=external_message_id,
            direction="inbound",
        )

        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
            payload=payload,
            max_attempts=3,
            idempotency_key=(f"crash-retry:{channel}:{provider_media_id}"),
        )

        job_id = job.id

        first = await JobWorker(
            db,
            worker_id="media-crash-worker-1",
        ).run_once(
            job_id=job_id,
        )

        assert first is not None
        assert first.status == "queued"
        assert first.attempts == 1

    # Physical storage already happened.
    assert storage_path.exists()

    # But failed handler DB writes must have rolled back.
    async with SessionLocal() as verify_db:
        attachment_count = await verify_db.scalar(
            select(CustomerServiceAttachment)
            .where(CustomerServiceAttachment.id == attachment_id)
            .with_only_columns(__import__("sqlalchemy").func.count())
        )

        link_count = await verify_db.scalar(
            select(CustomerServiceExternalMediaLink)
            .where(CustomerServiceExternalMediaLink.attachment_id == attachment_id)
            .with_only_columns(__import__("sqlalchemy").func.count())
        )

        assert attachment_count == 0
        assert link_count == 0

    # Make retry immediately due.
    async with SessionLocal() as db:
        job = await JobService(db).get(
            job_id=job_id,
            user_id=user_id,
        )

        job.run_after = datetime.now(timezone.utc)

        await db.commit()

        second = await JobWorker(
            db,
            worker_id="media-crash-worker-2",
        ).run_once(
            job_id=job_id,
        )

        assert second is not None
        assert second.status == "succeeded"
        assert second.attempts == 2
        assert second.result["attachment_id"] == str(attachment_id)

    async with SessionLocal() as verify_db:
        attachments = list(
            (
                await verify_db.execute(
                    select(CustomerServiceAttachment).where(
                        CustomerServiceAttachment.id == attachment_id
                    )
                )
            )
            .scalars()
            .all()
        )

        links = list(
            (
                await verify_db.execute(
                    select(CustomerServiceExternalMediaLink).where(
                        CustomerServiceExternalMediaLink.attachment_id == attachment_id
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(attachments) == 1
        assert len(links) == 1

        assert attachments[0].storage_key == storage_key

        assert links[0].provider_media_id == provider_media_id

    assert fetch_calls == 2
    assert link_calls == 2

    assert storage_path.exists()
    assert storage_path.read_bytes() == b"crash-retry-media"

    # Test cleanup only.
    storage_path.unlink(missing_ok=True)
