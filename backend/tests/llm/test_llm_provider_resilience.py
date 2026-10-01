from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.providers.llm.resilience import (
    LLMCircuitBreaker,
    LLMCircuitOpenError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResilienceMetrics,
    LLMRetryPolicy,
    execute_openai_with_resilience,
)
from app.runtime.nodes.builtins.llm_generate import (
    LlmGenerateConfig,
    LlmGenerateNode,
)


class FakeOpenAIRateLimitError(Exception):
    status_code = 429
    code = "rate_limit_exceeded"
    body = {"error": {"code": "rate_limit_exceeded"}}


class FakeOpenAIQuotaError(Exception):
    status_code = 429
    code = "insufficient_quota"
    body = {"error": {"code": "insufficient_quota"}}


@pytest.mark.asyncio
async def test_transient_rate_limit_uses_bounded_exponential_backoff():
    calls = 0
    sleeps: list[float] = []
    metrics = LLMResilienceMetrics()

    async def operation():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise FakeOpenAIRateLimitError()
        return "ok"

    async def fake_sleep(seconds: float):
        sleeps.append(seconds)

    result = await execute_openai_with_resilience(
        operation,
        policy=LLMRetryPolicy(
            max_attempts=3,
            base_seconds=2,
            max_seconds=30,
            jitter_ratio=0,
            circuit_failure_threshold=10,
        ),
        sleep=fake_sleep,
        jitter=lambda _start, _end: 0,
        breaker=LLMCircuitBreaker(),
        metrics=metrics,
    )

    assert result == "ok"
    assert calls == 3
    assert sleeps == [2, 4]
    assert metrics.snapshot()["openai.retry"] == 2
    assert metrics.snapshot()["openai.success"] == 1


@pytest.mark.asyncio
async def test_quota_error_is_classified_and_not_retried():
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        raise FakeOpenAIQuotaError()

    with pytest.raises(LLMQuotaExceededError) as raised:
        await execute_openai_with_resilience(
            operation,
            policy=LLMRetryPolicy(max_attempts=3),
            breaker=LLMCircuitBreaker(),
            metrics=LLMResilienceMetrics(),
        )

    assert calls == 1
    assert raised.value.code == "llm_quota_exceeded"
    assert raised.value.retryable is False


@pytest.mark.asyncio
async def test_circuit_opens_after_configured_transient_failure_threshold():
    breaker = LLMCircuitBreaker()
    policy = LLMRetryPolicy(
        max_attempts=1,
        circuit_failure_threshold=1,
        circuit_reset_seconds=60,
    )

    async def operation():
        raise FakeOpenAIRateLimitError()

    with pytest.raises(LLMRateLimitError):
        await execute_openai_with_resilience(
            operation,
            policy=policy,
            breaker=breaker,
            metrics=LLMResilienceMetrics(),
        )

    with pytest.raises(LLMCircuitOpenError):
        await execute_openai_with_resilience(
            operation,
            policy=policy,
            breaker=breaker,
            metrics=LLMResilienceMetrics(),
        )


class FailingGenerateClient:
    async def generate(self, **_kwargs):
        raise LLMRateLimitError(
            provider="openai",
            code="llm_rate_limited",
            message="OpenAI rate limit remained unavailable",
            retryable=True,
            status_code=429,
        )


def _runtime_context(*, attempt: int, max_attempts: int):
    tools = SimpleNamespace(llm=FailingGenerateClient())
    return SimpleNamespace(
        tools=tools,
        request=SimpleNamespace(state=SimpleNamespace(tools=tools)),
        extras={"_job": {"attempt": attempt, "max_attempts": max_attempts}},
    )


@pytest.mark.asyncio
async def test_llm_node_without_fallback_raises_provider_error():
    with pytest.raises(LLMRateLimitError):
        await LlmGenerateNode().run(
            _runtime_context(attempt=1, max_attempts=3),
            {"vars": {}},
            LlmGenerateConfig(prompt="reply", save_as="reply"),
        )


@pytest.mark.asyncio
async def test_llm_node_uses_handoff_fallback_on_first_attempt():
    result = await LlmGenerateNode().run(
        _runtime_context(attempt=1, max_attempts=3),
        {"vars": {}},
        LlmGenerateConfig(
            prompt="reply",
            save_as="reply",
            provider_failure_fallback="A human agent will review your message.",
        ),
    )

    assert result["output"] == "A human agent will review your message."
    assert result["patch"]["vars"]["reply"] == result["output"]
    assert result["meta"]["provider_failure_code"] == "llm_rate_limited"
    assert result["meta"]["degraded"] is True
    assert result["meta"]["handoff_required"] is True
