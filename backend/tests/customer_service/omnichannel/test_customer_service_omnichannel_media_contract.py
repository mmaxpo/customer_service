from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domains.customer_service.integrations.omnichannel.generic import (
    GenericOmnichannelAdapter,
)
from app.domains.customer_service.integrations.omnichannel.protocol import (
    NormalizedInboundMedia,
    NormalizedInboundMessage,
    NormalizedOutboundAttachment,
    NormalizedOutboundMessage,
)
from app.domains.customer_service.schemas.omnichannel import (
    OmnichannelInboundMedia,
    OmnichannelInboundMessage,
    OmnichannelOutboundAttachment,
    OmnichannelOutboundMessage,
)
from app.domains.customer_service.workflows.omnichannel_jobs import (
    send_omnichannel_outbound_job,
)


def test_inbound_contract_supports_media_only_message():
    message = OmnichannelInboundMessage(
        channel="whatsapp",
        external_account_id="acct-1",
        external_thread_id="thread-1",
        external_message_id="message-1",
        body="",
        media=[
            OmnichannelInboundMedia(
                provider_media_id="provider-media-1",
                filename="photo.jpg",
                content_type="image/jpeg",
                size_bytes=1234,
            )
        ],
    )

    assert message.body == ""
    assert len(message.media) == 1
    assert message.media[0].provider_media_id == "provider-media-1"

    with pytest.raises(ValidationError):
        OmnichannelInboundMessage(
            channel="whatsapp",
            external_account_id="acct-1",
            external_thread_id="thread-1",
            external_message_id="message-empty",
            body="",
        )


def test_outbound_contract_supports_attachment_only_message():
    attachment_id = uuid4()

    message = OmnichannelOutboundMessage(
        conversation_id=uuid4(),
        body="",
        attachments=[
            OmnichannelOutboundAttachment(
                attachment_id=attachment_id,
            )
        ],
    )

    assert message.body == ""
    assert message.attachments[0].attachment_id == attachment_id

    with pytest.raises(ValidationError):
        OmnichannelOutboundMessage(
            conversation_id=uuid4(),
            body="",
        )


def test_protocol_separates_provider_media_from_canonical_attachment():
    inbound = NormalizedInboundMessage(
        channel="instagram",
        external_account_id="acct-1",
        external_thread_id="thread-1",
        external_message_id="message-1",
        body="",
        media=[
            NormalizedInboundMedia(
                provider_media_id="ig-media-1",
                download_url=("https://provider.invalid/media/1"),
                filename="image.jpg",
                content_type="image/jpeg",
                size_bytes=42,
            )
        ],
    )

    canonical_id = uuid4()

    outbound = NormalizedOutboundMessage(
        user_id=uuid4(),
        conversation_id=uuid4(),
        channel="instagram",
        external_account_id="acct-1",
        external_thread_id="thread-1",
        body="",
        attachments=[
            NormalizedOutboundAttachment(
                attachment_id=canonical_id,
                filename="image.jpg",
                content_type="image/jpeg",
                size_bytes=42,
            )
        ],
    )

    assert inbound.media[0].provider_media_id == "ig-media-1"
    assert outbound.attachments[0].attachment_id == canonical_id

    with pytest.raises(ValidationError):
        NormalizedInboundMessage(
            channel="instagram",
            external_account_id="acct-1",
            external_thread_id="thread-1",
            external_message_id="empty-1",
            body="",
        )

    with pytest.raises(ValidationError):
        NormalizedOutboundMessage(
            user_id=uuid4(),
            conversation_id=uuid4(),
            channel="instagram",
            external_account_id="acct-1",
            external_thread_id="thread-1",
            body="",
        )


@pytest.mark.asyncio
async def test_generic_webhook_preserves_media_descriptor():
    adapter = GenericOmnichannelAdapter()

    event = await adapter.normalize_webhook_event(
        {
            "channel": "generic",
            "external_account_id": "acct-1",
            "external_thread_id": "thread-1",
            "external_message_id": "message-1",
            "body": "",
            "media": [
                {
                    "provider_media_id": "media-1",
                    "filename": "proof.png",
                    "content_type": "image/png",
                    "size_bytes": 12,
                }
            ],
        }
    )

    assert event.body == ""
    assert event.media[0].provider_media_id == "media-1"


@pytest.mark.asyncio
async def test_outbound_job_reconstructs_attachment_ids(
    monkeypatch,
):
    attachment_id = uuid4()
    conversation_id = uuid4()
    user_id = uuid4()

    captured = {}

    async def fake_send(
        self,
        *,
        user_id,
        payload,
    ):
        captured["user_id"] = user_id
        captured["payload"] = payload

        return {
            "conversation_id": payload.conversation_id,
            "message_id": uuid4(),
            "external_message_id": "provider-1",
            "channel": "generic",
            "external_account_id": "default",
            "external_thread_id": (
                payload.external_thread_id or str(payload.conversation_id)
            ),
            "delivery_status": "sent",
            "provider_response": None,
        }

    monkeypatch.setattr(
        (
            "app.domains.customer_service.services."
            "omnichannel."
            "CustomerServiceOmnichannelService."
            "send_outbound_message"
        ),
        fake_send,
    )

    ctx = SimpleNamespace(
        db=object(),
        job=SimpleNamespace(
            user_id=user_id,
            max_attempts=3,
            attempts=1,
        ),
    )

    await send_omnichannel_outbound_job(
        {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id),
            "body": "",
            "sender_type": "agent",
            "attachment_ids": [str(attachment_id)],
            "idempotency_key": "media-job-1",
        },
        ctx,
    )

    payload = captured["payload"]

    assert payload.body == ""
    assert len(payload.attachments) == 1
    assert payload.attachments[0].attachment_id == attachment_id
