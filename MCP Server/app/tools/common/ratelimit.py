# app/tools/common/ratelimit.py
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """
    Token bucket (qps/burst) + concurrency semaphore.

    Usage:
        limiter = RateLimiter(qps=3.0, burst=6, concurrency=6)
        async with limiter:
            ... do request ...
    """

    def __init__(self, qps: float = 5.0, burst: int = 10, concurrency: int = 10):
        self.qps = float(qps)
        self.burst = int(burst)
        self._tokens = float(burst)
        self._updated_at = time.monotonic()

        self._lock = asyncio.Lock()
        self._sem = asyncio.Semaphore(int(concurrency))

    def _refill(self) -> None:
        now = time.monotonic()
        dt = now - self._updated_at
        self._updated_at = now

        if self.qps <= 0:
            # unlimited QPS
            self._tokens = float(self.burst)
            return

        self._tokens = min(float(self.burst), self._tokens + dt * self.qps)

    async def acquire(self) -> None:
        # Limit concurrency first
        await self._sem.acquire()

        try:
            while True:
                async with self._lock:
                    self._refill()
                    if self._tokens >= 1.0:
                        self._tokens -= 1.0
                        return

                    # Need to wait for more tokens
                    missing = 1.0 - self._tokens
                    wait_sec = missing / self.qps if self.qps > 0 else 0.0

                # Sleep outside lock
                await asyncio.sleep(max(wait_sec, 0.001))
        except Exception:
            # if something crashes before returning, free concurrency slot
            self._sem.release()
            raise

    def release(self) -> None:
        self._sem.release()

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.release()