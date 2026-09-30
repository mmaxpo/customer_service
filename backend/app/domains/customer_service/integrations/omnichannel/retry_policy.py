from __future__ import annotations

from dataclasses import dataclass

from app.domains.customer_service.integrations.omnichannel.retry import (
    is_retryable_provider_error,
)


@dataclass(frozen=True)
class OmnichannelRetryDecision:
    should_retry: bool
    delay_seconds: int
    reason: str


class OmnichannelRetryPolicy:
    def __init__(
        self,
        *,
        max_attempts: int = 3,
        base_delay_seconds: int = 30,
        max_delay_seconds: int = 300,
    ):
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds

    def decide(self, *, exc: Exception, attempt: int) -> OmnichannelRetryDecision:
        if not is_retryable_provider_error(exc):
            return OmnichannelRetryDecision(
                should_retry=False,
                delay_seconds=0,
                reason="permanent_provider_error",
            )

        if attempt >= self.max_attempts:
            return OmnichannelRetryDecision(
                should_retry=False,
                delay_seconds=0,
                reason="max_attempts_exceeded",
            )

        delay = min(
            self.base_delay_seconds * (2 ** max(attempt - 1, 0)),
            self.max_delay_seconds,
        )

        return OmnichannelRetryDecision(
            should_retry=True,
            delay_seconds=delay,
            reason="transient_provider_error",
        )
