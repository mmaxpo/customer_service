from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select

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
from app.domains.customer_service.workflows.omnichannel_jobs import (
    materialize_omnichannel_inbound_media_job,
)
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


class _Job:
    def __init__(
        self,
        *,
        user_id,
    ):
        self.user_id = user_id
        self.attempts = 1
        self.max_attempts = 3


class _Ctx:
    def __init__(
        self,
        *,
        db,
        user_id,
    ):
        self.db = db
        self.job = _Job(
            user_id=user_id,
        )
        self.worker_id = "media-concurrency-test"
        self.retryable = True


@pytest.mark.asyncio
async def test_duplicate_media_materialization_is_serialized_and_fetches_once(
    monkeypatch,
):
    from app.domains.customer_service.workflows import (
        omnichannel_jobs as jobs_module,
    )

    channel = f"media-concurrency-{uuid4().hex}"
    external_account_id = "account-1"
    external_thread_id = "thread-1"
    external_message_id = "message-1"
    provider_media_id = "media-1"

    conversation_id = uuid4()
    message_id = uuid4()

    fetch_started = asyncio.Event()
    allow_first_fetch_to_finish = asyncio.Event()

    fetch_calls = 0

    class ConcurrentProvider:
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

            # Hold the first transaction after it owns the
            # advisory lock. A competing materialization should
            # block at the lock and never enter provider fetch.
            if fetch_calls == 1:
                fetch_started.set()

                await allow_first_fetch_to_finish.wait()

            return FetchedInboundMedia(
                content=b"concurrent-provider-media",
                filename="concurrent.jpg",
                content_type="image/jpeg",
                metadata={},
            )

    registry = get_omnichannel_provider_registry()

    test_adapters = dict(registry._adapters)
    test_adapters[channel] = ConcurrentProvider()
    monkeypatch.setattr(registry, "_adapters", test_adapters)

    # Keep our dynamic test provider registered.
    monkeypatch.setattr(
        jobs_module,
        "register_default_omnichannel_providers",
        lambda: None,
    )

    async with SessionLocal() as setup_db:
        owner = await create_user(
            UserCreate(
                email=(f"media-concurrency-{uuid4()}@example.com"),
                password=(f"Media-Concurrency-{uuid4()}"),
            ),
            setup_db,
        )

        workspace, _ = await WorkspaceService(setup_db).create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name=(f"Media Concurrency {uuid4()}")),
        )

        user_id = workspace.id

        customer = Customer(
            user_id=user_id,
            workspace_id=user_id,
            name="Concurrent Media Customer",
        )
        setup_db.add(customer)
        await setup_db.flush()

        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            workspace_id=user_id,
            customer_id=customer.id,
            channel=channel,
            subject="Concurrent inbound media",
            status="open",
        )
        setup_db.add(conversation)

        message = ConversationMessage(
            id=message_id,
            conversation_id=conversation_id,
            sender_type=MessageSenderType.CUSTOMER,
            body="",
        )
        setup_db.add(message)

        await setup_db.flush()

        repo = OmnichannelRepository(setup_db)

        await repo.create_connection(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            config={},
        )

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

        await setup_db.commit()

    payload = {
        "user_id": str(user_id),
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "channel": channel,
        "external_account_id": (external_account_id),
        "external_message_id": (external_message_id),
        "provider_media_id": (provider_media_id),
        "media": {
            "provider_media_id": (provider_media_id),
            "filename": "source.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 25,
            "metadata": {},
        },
    }

    async def run_one():
        async with SessionLocal() as db:
            result = await materialize_omnichannel_inbound_media_job(
                payload,
                _Ctx(
                    db=db,
                    user_id=user_id,
                ),
            )

            # Handler success normally commits later in JobWorker.
            # Reproduce that transaction boundary here.
            await db.commit()

            return result

    first_task = asyncio.create_task(run_one())

    await asyncio.wait_for(
        fetch_started.wait(),
        timeout=5,
    )

    second_task = asyncio.create_task(run_one())

    # Give the second transaction time to reach the lock.
    await asyncio.sleep(0.2)

    # The advisory lock must keep it out of provider fetch.
    assert fetch_calls == 1
    assert second_task.done() is False

    allow_first_fetch_to_finish.set()

    first_result, second_result = await asyncio.gather(
        first_task,
        second_task,
    )

    assert fetch_calls == 1

    statuses = {
        first_result["status"],
        second_result["status"],
    }

    assert statuses == {
        "materialized",
        "already_materialized",
    }

    assert first_result["attachment_id"] == second_result["attachment_id"]

    async with SessionLocal() as verify_db:
        attachments = list(
            (
                await verify_db.scalars(
                    select(CustomerServiceAttachment).where(
                        CustomerServiceAttachment.conversation_id == conversation_id
                    )
                )
            ).all()
        )

        links = list(
            (
                await verify_db.scalars(
                    select(CustomerServiceExternalMediaLink).where(
                        CustomerServiceExternalMediaLink.user_id == user_id,
                        CustomerServiceExternalMediaLink.channel == channel,
                        CustomerServiceExternalMediaLink.external_account_id
                        == external_account_id,
                        CustomerServiceExternalMediaLink.external_message_id
                        == external_message_id,
                        CustomerServiceExternalMediaLink.provider_media_id
                        == provider_media_id,
                    )
                )
            ).all()
        )

        assert len(attachments) == 1
        assert len(links) == 1

        assert links[0].attachment_id == attachments[0].id
