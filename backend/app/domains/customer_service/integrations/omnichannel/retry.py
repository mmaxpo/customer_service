from __future__ import annotations

from app.domains.customer_service.integrations.omnichannel.errors import (
    OmnichannelProviderError,
)


def is_retryable_provider_error(exc: Exception) -> bool:
    if isinstance(exc, OmnichannelProviderError):
        return exc.retryable

    return False
