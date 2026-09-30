from datetime import datetime, timedelta, timezone


class ExponentialBackoffRetry:
    def __init__(
        self,
        *,
        base_seconds: int = 2,
        max_seconds: int = 300,
    ):
        self.base_seconds = base_seconds
        self.max_seconds = max_seconds

    def next_retry_at(self, attempts: int) -> datetime:
        delay = min(
            self.max_seconds,
            self.base_seconds ** max(attempts, 1),
        )

        return datetime.now(timezone.utc) + timedelta(seconds=delay)
