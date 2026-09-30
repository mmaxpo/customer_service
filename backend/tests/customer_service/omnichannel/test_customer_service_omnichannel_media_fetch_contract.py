from __future__ import annotations

import pytest

from app.domains.customer_service.integrations.omnichannel.generic import (
    GenericOmnichannelAdapter,
)
from app.domains.customer_service.integrations.omnichannel.instagram import (
    InstagramOmnichannelAdapter,
)
from app.domains.customer_service.integrations.omnichannel.protocol import (
    FetchedInboundMedia,
    NormalizedInboundMedia,
    OmnichannelProviderConnectionContext,
)
from app.domains.customer_service.integrations.omnichannel.whatsapp import (
    WhatsAppOmnichannelAdapter,
)


def test_provider_media_fetch_protocol_is_provider_neutral():
    connection = OmnichannelProviderConnectionContext(
        channel="whatsapp",
        external_account_id="wa-account-1",
        config={
            "provider_setting": "opaque-value",
        },
    )

    media = NormalizedInboundMedia(
        provider_media_id="provider-media-1",
        filename="photo.jpg",
        content_type="image/jpeg",
        size_bytes=123,
    )

    fetched = FetchedInboundMedia(
        content=b"real-provider-bytes",
        filename=media.filename,
        content_type=media.content_type,
        metadata={
            "provider_media_id": media.provider_media_id,
        },
    )

    assert connection.channel == "whatsapp"
    assert connection.external_account_id == "wa-account-1"
    assert connection.config["provider_setting"] == "opaque-value"

    assert fetched.content == b"real-provider-bytes"
    assert fetched.filename == "photo.jpg"
    assert fetched.content_type == "image/jpeg"

    assert not hasattr(connection, "db")
    assert not hasattr(connection, "conversation_id")
    assert not hasattr(connection, "ticket_id")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "adapter",
    [
        GenericOmnichannelAdapter(),
        WhatsAppOmnichannelAdapter(),
        InstagramOmnichannelAdapter(),
    ],
)
async def test_unimplemented_media_fetch_fails_closed(adapter):
    media = NormalizedInboundMedia(
        provider_media_id="media-1",
        download_url="https://provider.invalid/media/1",
    )

    connection = OmnichannelProviderConnectionContext(
        channel=adapter.channel,
        external_account_id="account-1",
        config={},
    )

    with pytest.raises(NotImplementedError):
        await adapter.fetch_media(
            media=media,
            connection=connection,
        )


def test_fetched_media_does_not_contain_canonical_product_identity():
    fields = FetchedInboundMedia.model_fields

    assert "content" in fields
    assert "filename" in fields
    assert "content_type" in fields
    assert "metadata" in fields

    assert "attachment_id" not in fields
    assert "conversation_id" not in fields
    assert "message_id" not in fields
    assert "user_id" not in fields


def test_provider_connection_context_is_not_persistence_model():
    fields = OmnichannelProviderConnectionContext.model_fields

    assert set(fields) == {
        "channel",
        "external_account_id",
        "config",
    }
