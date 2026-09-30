from app.domains.customer_service.integrations.omnichannel.errors import (
    OmnichannelProviderPermanentError,
    OmnichannelProviderTransientError,
)
from app.domains.customer_service.integrations.omnichannel.retry import (
    is_retryable_provider_error,
)


def test_transient_provider_errors_are_retryable():
    exc = OmnichannelProviderTransientError("temporary outage", code="timeout")

    assert is_retryable_provider_error(exc) is True
    assert exc.retryable is True
    assert exc.code == "timeout"


def test_permanent_provider_errors_are_not_retryable():
    exc = OmnichannelProviderPermanentError("invalid recipient", code="bad_recipient")

    assert is_retryable_provider_error(exc) is False
    assert exc.retryable is False
    assert exc.code == "bad_recipient"


def test_unknown_errors_are_not_retryable_by_default():
    assert is_retryable_provider_error(RuntimeError("unknown")) is False
