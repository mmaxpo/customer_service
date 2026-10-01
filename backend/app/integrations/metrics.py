from dataclasses import dataclass


@dataclass
class IntegrationMetrics:
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    circuit_open: int = 0
    provider_failures: int = 0
    last_error: str | None = None


class InMemoryIntegrationMetrics:
    def __init__(self):
        self._items: dict[str, IntegrationMetrics] = {}

    def get(self, provider: str) -> IntegrationMetrics:
        if provider not in self._items:
            self._items[provider] = IntegrationMetrics()
        return self._items[provider]

    def snapshot(self) -> dict[str, IntegrationMetrics]:
        return dict(self._items)


metrics_registry = InMemoryIntegrationMetrics()
