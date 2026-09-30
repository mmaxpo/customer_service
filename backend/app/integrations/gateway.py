from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.integrations.circuit_breaker import CircuitBreaker
from app.integrations.errors import (
    IntegrationCircuitOpenError,
    IntegrationError,
    IntegrationProviderError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)
from app.integrations.metrics import metrics_registry
from app.integrations.policy import IntegrationPolicy


T = TypeVar("T")


class IntegrationGateway:
    """
    Generic reliability boundary for external integration reads.

    Only failures explicitly classified as transient are retried. Provider,
    authorization, validation, business, and unknown failures fail fast rather
    than being repeated blindly.

    Current application consumers use this gateway only for read operations.
    """

    def __init__(
        self,
        *,
        policy: IntegrationPolicy | None = None,
    ):
        self.policy = policy or IntegrationPolicy()
        self._breakers: dict[str, CircuitBreaker] = {}

    def _breaker_for(self, provider: str) -> CircuitBreaker:
        if provider not in self._breakers:
            self._breakers[provider] = CircuitBreaker(
                self.policy.circuit_breaker,
            )
        return self._breakers[provider]

    async def call(
        self,
        *,
        provider: str,
        operation: str,
        func: Callable[[], Awaitable[T]],
    ) -> T:
        key = f"{provider}.{operation}"
        metrics = metrics_registry.get(key)
        breaker = self._breaker_for(key)

        last_error: IntegrationError | None = None
        retry_after_seconds: float | None = None

        for attempt in range(
            1,
            self.policy.retry.max_attempts + 1,
        ):
            metrics.attempts += 1

            try:
                breaker.before_call()

                result = await asyncio.wait_for(
                    func(),
                    timeout=self.policy.timeout.timeout_seconds,
                )

                breaker.record_success()
                metrics.successes += 1
                return result

            except IntegrationCircuitOpenError as exc:
                metrics.circuit_open += 1
                metrics.last_error = str(exc)
                raise

            except TimeoutError:
                retry_after_seconds = None
                last_error = IntegrationTimeoutError(
                    f"{key} timed out after {self.policy.timeout.timeout_seconds}s"
                )
                metrics.timeouts += 1
                metrics.failures += 1
                metrics.last_error = str(last_error)
                breaker.record_failure()

            except IntegrationTimeoutError as exc:
                retry_after_seconds = None
                last_error = exc
                metrics.timeouts += 1
                metrics.failures += 1
                metrics.last_error = str(exc)
                breaker.record_failure()

            except IntegrationUnavailableError as exc:
                retry_after_seconds = exc.retry_after_seconds
                last_error = exc
                metrics.provider_failures += 1
                metrics.failures += 1
                metrics.last_error = str(exc)
                breaker.record_failure()

            except IntegrationProviderError as exc:
                metrics.provider_failures += 1
                metrics.failures += 1
                metrics.last_error = str(exc)
                raise

            except IntegrationError as exc:
                metrics.provider_failures += 1
                metrics.failures += 1
                metrics.last_error = str(exc)
                raise

            except Exception as exc:
                wrapped = IntegrationProviderError(f"{key} failed: {exc}")
                metrics.provider_failures += 1
                metrics.failures += 1
                metrics.last_error = str(wrapped)
                raise wrapped from exc

            if attempt < self.policy.retry.max_attempts:
                policy_backoff = self.policy.retry.backoff_seconds * attempt
                delay = max(
                    policy_backoff,
                    retry_after_seconds or 0.0,
                )
                await asyncio.sleep(delay)

        assert last_error is not None
        raise last_error


default_gateway = IntegrationGateway()
