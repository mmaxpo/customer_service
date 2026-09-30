from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domains.customer_service.integrations.omnichannel.protocol import (
    FetchedInboundMedia,
    NormalizedInboundMedia,
    NormalizedInboundMessage,
    NormalizedOutboundMessage,
    NormalizedOutboundResult,
    OmnichannelProviderConnectionContext,
)


class OmnichannelProviderAdapter(ABC):
    """Provider boundary for WhatsApp, Instagram, email, chat, and future channels.

    Adapters must not know about tickets, conversations, workflows, or SQLAlchemy.
    They only verify/normalize external payloads and send provider messages.
    """

    channel: str

    async def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> bool:
        return True

    async def normalize_inbound(
        self,
        *,
        external_account_id: str,
        payload: dict[str, Any],
    ) -> list[NormalizedInboundMessage]:
        raise NotImplementedError

    async def fetch_media(
        self,
        *,
        media: NormalizedInboundMedia,
        connection: OmnichannelProviderConnectionContext,
    ) -> FetchedInboundMedia:
        """Fetch provider media without exposing provider transport to product code."""

        raise NotImplementedError(
            f"{self.channel} provider does not implement inbound media fetching"
        )

    @abstractmethod
    async def send_message(
        self,
        message: NormalizedOutboundMessage,
    ) -> NormalizedOutboundResult:
        raise NotImplementedError
