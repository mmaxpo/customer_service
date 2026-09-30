from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.05


@dataclass(frozen=True)
class TimeoutPolicy:
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 5
    recovery_seconds: float = 30.0


@dataclass(frozen=True)
class IntegrationPolicy:
    retry: RetryPolicy = RetryPolicy()
    timeout: TimeoutPolicy = TimeoutPolicy()
    circuit_breaker: CircuitBreakerPolicy = CircuitBreakerPolicy()
