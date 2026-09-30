from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domains.customer_service.integrations.omnichannel.protocol import (
    NormalizedInboundMedia,
)
from app.domains.customer_service.schemas.omnichannel import (
    OmnichannelInboundMedia,
)


def test_api_media_requires_stable_provider_media_identity():
    with pytest.raises(ValidationError):
        OmnichannelInboundMedia(
            download_url="https://provider.invalid/media/1",
            filename="photo.jpg",
        )

    media = OmnichannelInboundMedia(
        provider_media_id="provider-media-1",
        download_url="https://provider.invalid/media/1",
    )

    assert media.provider_media_id == "provider-media-1"


def test_provider_protocol_media_requires_stable_provider_media_identity():
    with pytest.raises(ValidationError):
        NormalizedInboundMedia(
            download_url="https://provider.invalid/media/1",
        )

    media = NormalizedInboundMedia(
        provider_media_id="provider-media-1",
    )

    assert media.provider_media_id == "provider-media-1"


@pytest.mark.asyncio
async def test_inbound_media_jobs_are_enqueued_before_event_commit(
    monkeypatch,
):
    from app.domains.customer_service.services import omnichannel as module

    user_id = uuid4()
    conversation_id = uuid4()
    message_id = uuid4()
    customer_id = uuid4()

    sequence: list[tuple] = []

    class FakeRepo:
        async def get_external_message(self, **kwargs):
            return None

        async def get_external_conversation(self, **kwargs):
            return type(
                "ExternalConversation",
                (),
                {
                    "conversation_id": conversation_id,
                    "customer_id": customer_id,
                },
            )()

        async def link_external_message(self, **kwargs):
            return type(
                "Link",
                (),
                {
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                },
            )()

    class FakeConversationRepo:
        async def get_by_id(self, value):
            return type(
                "Conversation",
                (),
                {
                    "id": conversation_id,
                    "customer_id": customer_id,
                    "merged_into_id": None,
                    "channel": "generic",
                },
            )()

        async def update_message_meta(self, **kwargs):
            return None

    class FakeTicketRepo:
        async def get_by_conversation_id(self, value):
            return None

    class FakeInboxService:
        async def add_message(self, **kwargs):
            return type(
                "Message",
                (),
                {
                    "id": message_id,
                    "meta": {},
                },
            )()

    class FakeDB:
        async def execute(self, *args, **kwargs):
            return None

        async def get(self, model, value):
            return type(
                "Customer",
                (),
                {"id": customer_id},
            )()

    async def fake_enqueue(
        self,
        *,
        user_id,
        job_type,
        payload,
        max_attempts,
        idempotency_key,
        commit=True,
        **kwargs,
    ):
        assert commit is False
        sequence.append(
            (
                "job",
                job_type,
                payload["provider_media_id"],
                idempotency_key,
            )
        )

        return type(
            "Job",
            (),
            {
                "id": uuid4(),
                "job_type": job_type,
                "status": "queued",
                "payload": payload,
            },
        )()

    async def fake_publish(
        self,
        *,
        user_id,
        event_type,
        payload,
        meta=None,
    ):
        sequence.append(
            (
                "event",
                event_type,
            )
        )

    monkeypatch.setattr(
        module.JobService,
        "enqueue",
        fake_enqueue,
    )

    monkeypatch.setattr(
        module.CustomerServiceOmnichannelService,
        "_publish_event",
        fake_publish,
    )

    service = module.CustomerServiceOmnichannelService(FakeDB())

    service.omnichannel_repo = FakeRepo()
    service.conversation_repo = FakeConversationRepo()
    service.ticket_repo = FakeTicketRepo()
    service.inbox_service = FakeInboxService()

    payload = module.OmnichannelInboundMessage(
        channel="generic",
        external_account_id="account-1",
        external_thread_id="thread-1",
        external_message_id="message-1",
        body="",
        external_customer_id="customer-1",
        media=[
            OmnichannelInboundMedia(
                provider_media_id="media-1",
                filename="one.jpg",
            ),
            OmnichannelInboundMedia(
                provider_media_id="media-2",
                filename="two.jpg",
            ),
        ],
    )

    result = await service.ingest_inbound_message(
        user_id=user_id,
        payload=payload,
    )

    assert result["duplicate"] is False

    assert [item[0] for item in sequence] == [
        "job",
        "job",
        "event",
    ]

    assert sequence[0][2] == "media-1"
    assert sequence[1][2] == "media-2"

    assert sequence[0][3] != sequence[1][3]


@pytest.mark.asyncio
async def test_duplicate_inbound_message_does_not_schedule_media_again(
    monkeypatch,
):
    from app.domains.customer_service.services import omnichannel as module

    user_id = uuid4()
    conversation_id = uuid4()
    message_id = uuid4()
    customer_id = uuid4()

    scheduled = []

    class FakeRepo:
        async def get_external_message(self, **kwargs):
            return type(
                "Link",
                (),
                {
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                },
            )()

    class FakeTicketRepo:
        async def get_by_conversation_id(self, value):
            return None

    class FakeConversationRepo:
        async def get_by_id(self, value):
            return type(
                "Conversation",
                (),
                {
                    "id": conversation_id,
                    "customer_id": customer_id,
                },
            )()

    class FakeDB:
        async def execute(self, *args, **kwargs):
            return None

    async def fake_enqueue(self, **kwargs):
        scheduled.append(kwargs)
        raise AssertionError("duplicate delivery must not enqueue another media job")

    monkeypatch.setattr(
        module.JobService,
        "enqueue",
        fake_enqueue,
    )

    service = module.CustomerServiceOmnichannelService(FakeDB())
    service.omnichannel_repo = FakeRepo()
    service.ticket_repo = FakeTicketRepo()
    service.conversation_repo = FakeConversationRepo()

    payload = module.OmnichannelInboundMessage(
        channel="generic",
        external_account_id="account-1",
        external_thread_id="thread-1",
        external_message_id="message-1",
        body="text",
        media=[
            OmnichannelInboundMedia(
                provider_media_id="media-1",
            ),
        ],
    )

    result = await service.ingest_inbound_message(
        user_id=user_id,
        payload=payload,
    )

    assert result["duplicate"] is True
    assert scheduled == []
