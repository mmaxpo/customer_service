from __future__ import annotations

from app.domains.customer_service.integrations.omnichannel.generic import (
    GenericOmnichannelAdapter,
)
from app.domains.customer_service.integrations.omnichannel.protocol import (
    OmnichannelProviderCapabilities,
)
from app.domains.customer_service.schemas.omnichannel import (
    OmnichannelInboundMessage,
)


class InstagramOmnichannelAdapter(GenericOmnichannelAdapter):
    channel = "instagram"

    def capabilities(self) -> OmnichannelProviderCapabilities:
        return OmnichannelProviderCapabilities(
            channel=self.channel,
            supports_inbound=True,
            supports_outbound=True,
            supports_delivery_receipts=True,
            supports_read_receipts=True,
            supports_typing_indicators=False,
            supports_attachments=True,
            supports_templates=False,
        )

    async def normalize_inbound_message(
        self,
        payload: dict,
    ) -> OmnichannelInboundMessage:
        sender = payload.get("sender", {})

        return OmnichannelInboundMessage(
            channel="instagram",
            external_account_id=payload["external_account_id"],
            external_thread_id=payload["external_thread_id"],
            external_message_id=payload["external_message_id"],
            external_customer_id=payload["external_customer_id"],
            customer_name=sender.get("name") or sender.get("username"),
            body=payload["body"],
            raw_payload=payload,
        )
