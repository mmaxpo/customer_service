from __future__ import annotations

from uuid import uuid4

from app.domains.customer_service.integrations.omnichannel.protocol import (
    FetchedInboundMedia,
    NormalizedDeliveryEvent,
    NormalizedInboundMedia,
    NormalizedOutboundMessage,
    NormalizedOutboundResult,
    OmnichannelProviderConnectionContext,
    OmnichannelDeliveryStatus,
    WebhookVerificationResult,
    OmnichannelProviderCapabilities,
)
from app.domains.customer_service.schemas.omnichannel import (
    OmnichannelInboundMessage,
    OmnichannelWebhookEvent,
    OmnichannelWebhookEventType,
)


class GenericOmnichannelAdapter:
    channel = "generic"

    def capabilities(self) -> OmnichannelProviderCapabilities:
        return OmnichannelProviderCapabilities(
            channel=self.channel,
        )

    async def verify_webhook_signature(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> WebhookVerificationResult:
        return WebhookVerificationResult(
            verified=True,
            reason=None,
        )

    async def normalize_inbound_message(
        self,
        payload: dict,
    ) -> OmnichannelInboundMessage:
        return OmnichannelInboundMessage(**payload)

    async def normalize_webhook_event(
        self,
        payload: dict,
    ) -> OmnichannelWebhookEvent:
        return OmnichannelWebhookEvent(
            provider=self.channel,
            event_type=OmnichannelWebhookEventType.MESSAGE_INBOUND,
            channel=payload.get("channel", self.channel),
            external_account_id=payload["external_account_id"],
            external_thread_id=payload.get("external_thread_id"),
            external_message_id=payload.get("external_message_id"),
            external_customer_id=payload.get("external_customer_id"),
            customer_name=payload.get("customer_name"),
            customer_email=payload.get("customer_email"),
            customer_phone=payload.get("customer_phone"),
            body=payload.get("body") or "",
            media=payload.get("media") or [],
            raw_payload=payload,
            meta=payload.get("meta"),
        )

    async def normalize_delivery_event(
        self,
        payload: dict,
    ) -> NormalizedDeliveryEvent:
        return NormalizedDeliveryEvent(**payload)

    async def fetch_media(
        self,
        *,
        media: NormalizedInboundMedia,
        connection: OmnichannelProviderConnectionContext,
    ) -> FetchedInboundMedia:
        del media, connection

        # Generic transport has no trusted provider-specific media fetcher.
        # Never dereference arbitrary webhook-supplied URLs here.
        raise NotImplementedError(
            "generic provider does not implement inbound media fetching"
        )

    async def send_message(
        self,
        message: NormalizedOutboundMessage,
    ) -> NormalizedOutboundResult:
        external_message_id = message.idempotency_key or f"generic-{uuid4()}"

        return NormalizedOutboundResult(
            external_message_id=external_message_id,
            delivery_status=OmnichannelDeliveryStatus.SENT,
            raw_response={
                "provider": self.channel,
                "external_message_id": external_message_id,
            },
        )
