from __future__ import annotations

import asyncio
import logging
import random
import threading
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar


_T = TypeVar("_T")
_log = logging.getLogger("tajeran.llm.resilience")


@dataclass(frozen=True)
class LLMRetryPolicy:
    max_attempts: int = 3
    base_seconds: float = 2.0
    max_seconds: float = 30.0
    jitter_ratio: float = 0.25
    circuit_failure_threshold: int = 5
    circuit_reset_seconds: float = 60.0

    @classmethod
    def from_settings(cls, settings: Any) -> "LLMRetryPolicy":
        return cls(
            max_attempts=max(1, int(settings.LLM_PROVIDER_MAX_ATTEMPTS)),
            base_seconds=max(0.0, float(settings.LLM_RETRY_BASE_SECONDS)),
            max_seconds=max(0.0, float(settings.LLM_RETRY_MAX_SECONDS)),
            circuit_failure_threshold=max(
                1,
                int(settings.LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD),
            ),
            circuit_reset_seconds=max(
                1.0,
                float(settings.LLM_CIRCUIT_BREAKER_RESET_SECONDS),
            ),
        )


class LLMProviderError(RuntimeError):
    def __init__(
        self,
        *,
        provider: str,
        code: str,
        message: str,
        retryable: bool,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.provider = provider
        self.code = code
        self.retryable = retryable
        self.status_code = status_code
        self.retry_after = retry_after


class LLMRateLimitError(LLMProviderError):
    pass


class LLMQuotaExceededError(LLMProviderError):
    pass


class LLMProviderTransientError(LLMProviderError):
    pass


class LLMCircuitOpenError(LLMProviderError):
    pass


class LLMProviderRequestError(LLMProviderError):
    pass


class LLMResilienceMetrics:
    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = threading.Lock()

    def increment(self, key: str) -> None:
        with self._lock:
            self._counts[key] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


class LLMCircuitBreaker:
    def __init__(self) -> None:
        self._failures: Counter[str] = Counter()
        self._open_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def before_call(self, provider: str) -> None:
        now = time.monotonic()
        with self._lock:
            open_until = self._open_until.get(provider, 0.0)
            if open_until > now:
                raise LLMCircuitOpenError(
                    provider=provider,
                    code="llm_circuit_open",
                    message=f"{provider} is temporarily unavailable",
                    retryable=True,
                    retry_after=open_until - now,
                )
            if open_until:
                self._open_until.pop(provider, None)
                self._failures[provider] = 0

    def record_success(self, provider: str) -> None:
        with self._lock:
            self._failures[provider] = 0
            self._open_until.pop(provider, None)

    def record_failure(
        self,
        provider: str,
        *,
        threshold: int,
        reset_seconds: float,
    ) -> bool:
        with self._lock:
            self._failures[provider] += 1
            if self._failures[provider] < threshold:
                return False
            self._open_until[provider] = time.monotonic() + reset_seconds
            return True

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._open_until.clear()


llm_resilience_metrics = LLMResilienceMetrics()
llm_circuit_breaker = LLMCircuitBreaker()


def _provider_error_details(exc: Exception) -> tuple[int | None, str | None]:
    status_code = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    body = getattr(exc, "body", None)

    if isinstance(body, dict):
        error = body.get("error") if isinstance(body.get("error"), dict) else body
        code = code or error.get("code") or error.get("type")

    try:
        status_code = int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        status_code = None

    return status_code, str(code).strip().lower() if code else None


def _retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None

    raw = headers.get("retry-after") or headers.get("Retry-After")
    try:
        return max(0.0, float(raw)) if raw is not None else None
    except (TypeError, ValueError):
        return None


def classify_openai_error(exc: Exception) -> LLMProviderError | None:
    if isinstance(exc, LLMProviderError):
        return exc

    status_code, provider_code = _provider_error_details(exc)
    class_name = type(exc).__name__.lower()
    retry_after = _retry_after_seconds(exc)

    quota_codes = {
        "billing_hard_limit_reached",
        "insufficient_quota",
        "quota_exceeded",
    }
    if provider_code in quota_codes:
        return LLMQuotaExceededError(
            provider="openai",
            code="llm_quota_exceeded",
            message="OpenAI quota or billing limit was reached",
            retryable=False,
            status_code=status_code,
        )

    if status_code == 429 or "ratelimit" in class_name:
        return LLMRateLimitError(
            provider="openai",
            code="llm_rate_limited",
            message="OpenAI rate limit remained unavailable",
            retryable=True,
            status_code=status_code or 429,
            retry_after=retry_after,
        )

    if (
        status_code is not None
        and status_code >= 500
        or "timeout" in class_name
        or "connection" in class_name
    ):
        return LLMProviderTransientError(
            provider="openai",
            code="llm_provider_transient",
            message="OpenAI is temporarily unavailable",
            retryable=True,
            status_code=status_code,
            retry_after=retry_after,
        )

    if status_code is not None and status_code >= 400:
        return LLMProviderRequestError(
            provider="openai",
            code="llm_provider_request_rejected",
            message="OpenAI rejected the request",
            retryable=False,
            status_code=status_code,
        )

    return None


def is_llm_provider_failure_message(value: str) -> bool:
    normalized = str(value or "").lower()
    return any(
        code in normalized
        for code in (
            "llm_circuit_open",
            "llm_provider_request_rejected",
            "llm_provider_transient",
            "llm_quota_exceeded",
            "llm_rate_limited",
        )
    )


async def execute_openai_with_resilience(
    operation: Callable[[], Awaitable[_T]],
    *,
    policy: LLMRetryPolicy,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    jitter: Callable[[float, float], float] = random.uniform,
    breaker: LLMCircuitBreaker = llm_circuit_breaker,
    metrics: LLMResilienceMetrics = llm_resilience_metrics,
) -> _T:
    provider = "openai"
    breaker.before_call(provider)

    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = await operation()
        except Exception as exc:
            error = classify_openai_error(exc)
            if error is None:
                raise

            metrics.increment(f"{provider}.{error.code}")

            if not error.retryable:
                if isinstance(error, LLMQuotaExceededError):
                    opened = breaker.record_failure(
                        provider,
                        threshold=1,
                        reset_seconds=policy.circuit_reset_seconds,
                    )
                    if opened:
                        metrics.increment(f"{provider}.circuit_opened")
                _log.error(
                    "llm_provider_failure",
                    extra={
                        "provider": provider,
                        "failure_code": error.code,
                        "status_code": error.status_code,
                        "retryable": False,
                    },
                )
                raise error from exc

            opened = breaker.record_failure(
                provider,
                threshold=policy.circuit_failure_threshold,
                reset_seconds=policy.circuit_reset_seconds,
            )
            if opened:
                metrics.increment(f"{provider}.circuit_opened")

            if attempt >= policy.max_attempts:
                _log.error(
                    "llm_provider_retries_exhausted",
                    extra={
                        "provider": provider,
                        "failure_code": error.code,
                        "status_code": error.status_code,
                        "attempts": attempt,
                    },
                )
                raise error from exc

            exponential = min(
                policy.max_seconds,
                policy.base_seconds * (2 ** (attempt - 1)),
            )
            jitter_max = exponential * policy.jitter_ratio
            delay = min(
                policy.max_seconds,
                exponential + jitter(0.0, jitter_max),
            )
            if error.retry_after is not None:
                delay = max(delay, min(policy.max_seconds, error.retry_after))

            metrics.increment(f"{provider}.retry")
            _log.warning(
                "llm_provider_retry_scheduled",
                extra={
                    "provider": provider,
                    "failure_code": error.code,
                    "status_code": error.status_code,
                    "attempt": attempt,
                    "max_attempts": policy.max_attempts,
                    "retry_in_seconds": round(delay, 3),
                },
            )
            await sleep(delay)
        else:
            breaker.record_success(provider)
            metrics.increment(f"{provider}.success")
            return result

    raise AssertionError("unreachable LLM resilience state")


__all__ = [
    "LLMCircuitBreaker",
    "LLMCircuitOpenError",
    "LLMProviderError",
    "LLMProviderRequestError",
    "LLMProviderTransientError",
    "LLMQuotaExceededError",
    "LLMRateLimitError",
    "LLMResilienceMetrics",
    "LLMRetryPolicy",
    "classify_openai_error",
    "execute_openai_with_resilience",
    "is_llm_provider_failure_message",
    "llm_circuit_breaker",
    "llm_resilience_metrics",
]
