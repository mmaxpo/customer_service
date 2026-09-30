from app.domains.customer_service.integrations.omnichannel.errors import (
    OmnichannelProviderPermanentError,
    OmnichannelProviderTransientError,
)
from app.domains.customer_service.integrations.omnichannel.retry_policy import (
    OmnichannelRetryPolicy,
)


def test_retry_policy_retries_transient_provider_error_with_backoff():
    policy = OmnichannelRetryPolicy(
        max_attempts=3,
        base_delay_seconds=10,
        max_delay_seconds=60,
    )

    first = policy.decide(
        exc=OmnichannelProviderTransientError("timeout"),
        attempt=1,
    )
    second = policy.decide(
        exc=OmnichannelProviderTransientError("timeout"),
        attempt=2,
    )

    assert first.should_retry is True
    assert first.delay_seconds == 10
    assert first.reason == "transient_provider_error"

    assert second.should_retry is True
    assert second.delay_seconds == 20


def test_retry_policy_stops_after_max_attempts():
    policy = OmnichannelRetryPolicy(max_attempts=3)

    decision = policy.decide(
        exc=OmnichannelProviderTransientError("timeout"),
        attempt=3,
    )

    assert decision.should_retry is False
    assert decision.reason == "max_attempts_exceeded"


def test_retry_policy_does_not_retry_permanent_provider_error():
    policy = OmnichannelRetryPolicy()

    decision = policy.decide(
        exc=OmnichannelProviderPermanentError("invalid recipient"),
        attempt=1,
    )

    assert decision.should_retry is False
    assert decision.delay_seconds == 0
    assert decision.reason == "permanent_provider_error"


def test_retry_policy_does_not_retry_unknown_errors_by_default():
    policy = OmnichannelRetryPolicy()

    decision = policy.decide(
        exc=RuntimeError("unknown"),
        attempt=1,
    )

    assert decision.should_retry is False
    assert decision.reason == "permanent_provider_error"
