import time
from dataclasses import dataclass

from app.integrations.errors import IntegrationCircuitOpenError
from app.integrations.policy import CircuitBreakerPolicy


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    def __init__(self, policy: CircuitBreakerPolicy):
        self.policy = policy
        self.state = CircuitState()

    def before_call(self) -> None:
        if self.state.opened_at is None:
            return

        elapsed = time.monotonic() - self.state.opened_at

        if elapsed >= self.policy.recovery_seconds:
            self.state.failures = 0
            self.state.opened_at = None
            return

        raise IntegrationCircuitOpenError("Integration circuit is open")

    def record_success(self) -> None:
        self.state.failures = 0
        self.state.opened_at = None

    def record_failure(self) -> None:
        self.state.failures += 1

        if self.state.failures >= self.policy.failure_threshold:
            self.state.opened_at = time.monotonic()
