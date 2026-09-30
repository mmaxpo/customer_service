import asyncio

import pytest

from app.integrations.errors import (
    IntegrationCircuitOpenError,
    IntegrationError,
    IntegrationProviderError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)
from app.integrations.gateway import IntegrationGateway
from app.integrations.policy import (
    CircuitBreakerPolicy,
    IntegrationPolicy,
    RetryPolicy,
    TimeoutPolicy,
)


@pytest.mark.asyncio
async def test_gateway_success():
    gateway = IntegrationGateway()

    async def provider_call():
        return {"ok": True}

    result = await gateway.call(
        provider="test",
        operation="success",
        func=provider_call,
    )

    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_gateway_retries_transient_unavailable_then_success():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=3,
                backoff_seconds=0,
            ),
        )
    )

    calls = {"count": 0}

    async def provider_call():
        calls["count"] += 1

        if calls["count"] < 2:
            raise IntegrationUnavailableError("provider temporarily unavailable")

        return "ok"

    result = await gateway.call(
        provider="test",
        operation="retry",
        func=provider_call,
    )

    assert result == "ok"
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_gateway_retries_explicit_timeout_subtype_then_success():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=3,
                backoff_seconds=0,
            ),
        )
    )

    calls = {"count": 0}

    async def provider_call():
        calls["count"] += 1

        if calls["count"] == 1:
            raise IntegrationTimeoutError("provider transport timeout")

        return "ok"

    result = await gateway.call(
        provider="test",
        operation="timeout-retry",
        func=provider_call,
    )

    assert result == "ok"
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_gateway_outer_timeout_becomes_integration_timeout():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=1,
                backoff_seconds=0,
            ),
            timeout=TimeoutPolicy(
                timeout_seconds=0.01,
            ),
        )
    )

    async def provider_call():
        await asyncio.sleep(0.05)
        return "too late"

    with pytest.raises(IntegrationTimeoutError):
        await gateway.call(
            provider="test",
            operation="timeout",
            func=provider_call,
        )


@pytest.mark.asyncio
async def test_gateway_preserves_timeout_after_retry_exhaustion():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=2,
                backoff_seconds=0,
            ),
        )
    )

    calls = {"count": 0}
    expected = IntegrationTimeoutError("provider timed out")

    async def provider_call():
        calls["count"] += 1
        raise expected

    with pytest.raises(IntegrationTimeoutError) as caught:
        await gateway.call(
            provider="test",
            operation="timeout-exhaustion",
            func=provider_call,
        )

    assert caught.value is expected
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_gateway_preserves_unavailable_after_retry_exhaustion():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=2,
                backoff_seconds=0,
            ),
        )
    )

    calls = {"count": 0}
    expected = IntegrationUnavailableError("provider unavailable")

    async def provider_call():
        calls["count"] += 1
        raise expected

    with pytest.raises(IntegrationUnavailableError) as caught:
        await gateway.call(
            provider="test",
            operation="unavailable-exhaustion",
            func=provider_call,
        )

    assert caught.value is expected
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_gateway_provider_error_fails_fast_without_retry():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=3,
                backoff_seconds=0,
            ),
        )
    )

    calls = {"count": 0}
    expected = IntegrationProviderError("authorization rejected")

    async def provider_call():
        calls["count"] += 1
        raise expected

    with pytest.raises(IntegrationProviderError) as caught:
        await gateway.call(
            provider="test",
            operation="provider-error",
            func=provider_call,
        )

    assert caught.value is expected
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_gateway_unknown_integration_error_fails_fast():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=3,
                backoff_seconds=0,
            ),
        )
    )

    calls = {"count": 0}
    expected = IntegrationError("classified but non-transient")

    async def provider_call():
        calls["count"] += 1
        raise expected

    with pytest.raises(IntegrationError) as caught:
        await gateway.call(
            provider="test",
            operation="integration-error",
            func=provider_call,
        )

    assert caught.value is expected
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_gateway_unknown_exception_is_wrapped_and_not_retried():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=3,
                backoff_seconds=0,
            ),
        )
    )

    calls = {"count": 0}

    async def provider_call():
        calls["count"] += 1
        raise RuntimeError("unexpected provider bug")

    with pytest.raises(
        IntegrationProviderError,
        match="unexpected provider bug",
    ):
        await gateway.call(
            provider="test",
            operation="unknown",
            func=provider_call,
        )

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_gateway_circuit_breaker_opens_after_transient_failure():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=1,
                backoff_seconds=0,
            ),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=1,
                recovery_seconds=60,
            ),
        )
    )

    calls = {"count": 0}

    async def provider_call():
        calls["count"] += 1
        raise IntegrationUnavailableError("provider down")

    with pytest.raises(IntegrationUnavailableError):
        await gateway.call(
            provider="test",
            operation="circuit",
            func=provider_call,
        )

    assert calls["count"] == 1

    with pytest.raises(IntegrationCircuitOpenError):
        await gateway.call(
            provider="test",
            operation="circuit",
            func=provider_call,
        )

    # Open circuit rejects before invoking provider again.
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_provider_error_does_not_open_circuit():
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=1,
                backoff_seconds=0,
            ),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=1,
                recovery_seconds=60,
            ),
        )
    )

    calls = {"count": 0}

    async def provider_call():
        calls["count"] += 1

        if calls["count"] == 1:
            raise IntegrationProviderError("bad credentials")

        return "ok"

    with pytest.raises(IntegrationProviderError):
        await gateway.call(
            provider="test",
            operation="provider-error-circuit",
            func=provider_call,
        )

    result = await gateway.call(
        provider="test",
        operation="provider-error-circuit",
        func=provider_call,
    )

    assert result == "ok"
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_gateway_honors_retry_after_for_unavailable_failure(
    monkeypatch,
):
    gateway = IntegrationGateway(
        policy=IntegrationPolicy(
            retry=RetryPolicy(
                max_attempts=2,
                backoff_seconds=0.05,
            ),
        )
    )

    calls = {"count": 0}
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(
        "app.integrations.gateway.asyncio.sleep",
        fake_sleep,
    )

    async def provider_call():
        calls["count"] += 1

        if calls["count"] == 1:
            raise IntegrationUnavailableError(
                "rate limited",
                retry_after_seconds=2.5,
            )

        return "ok"

    result = await gateway.call(
        provider="test",
        operation="retry-after",
        func=provider_call,
    )

    assert result == "ok"
    assert calls["count"] == 2
    assert sleeps == [2.5]
