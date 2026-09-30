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


class WhatsAppOmnichannelAdapter(GenericOmnichannelAdapter):
    channel = "whatsapp"

    def capabilities(self) -> OmnichannelProviderCapabilities:
        return OmnichannelProviderCapabilities(
            channel=self.channel,
            supports_inbound=True,
            supports_outbound=True,
            supports_delivery_receipts=True,
            supports_read_receipts=True,
            supports_typing_indicators=False,
            supports_attachments=True,
            supports_templates=True,
        )

    async def normalize_inbound_message(
        self,
        payload: dict,
    ) -> OmnichannelInboundMessage:
        customer_profile = payload.get("profile", {})

        return OmnichannelInboundMessage(
            channel="whatsapp",
            external_account_id=payload["external_account_id"],
            external_thread_id=payload["external_thread_id"],
            external_message_id=payload["external_message_id"],
            external_customer_id=payload["external_customer_id"],
            customer_name=customer_profile.get("name"),
            customer_phone=payload.get("customer_phone"),
            body=payload["body"],
            raw_payload=payload,
        )
