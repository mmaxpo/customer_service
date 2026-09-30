from __future__ import annotations

from app.domains.customer_service.integrations.omnichannel.generic import (
    GenericOmnichannelAdapter,
)
from app.domains.customer_service.integrations.omnichannel.whatsapp import (
    WhatsAppOmnichannelAdapter,
)
from app.domains.customer_service.integrations.omnichannel.instagram import (
    InstagramOmnichannelAdapter,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)


def register_default_omnichannel_providers() -> None:
    registry = get_omnichannel_provider_registry()
    registry.register(GenericOmnichannelAdapter())
    registry.register(WhatsAppOmnichannelAdapter())
    registry.register(InstagramOmnichannelAdapter())
