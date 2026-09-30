from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class RateLimiter:
    """
    Simple async token_control bucket + concurrency cap.
    - qps: maximum average requests per second
    - burst: max bucket size
    - concurrency: max in-flight requests
    """

    qps: float = 5.0
    burst: int = 10
    concurrency: int = 10

    def __post_init__(self):
        self._tokens = float(self.burst)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()
        self._sem = asyncio.Semaphore(self.concurrency)

    async def acquire(self):
        await self._sem.acquire()
        await self._acquire_token()

    def release(self):
        self._sem.release()

    async def _acquire_token(self):
        async with self._lock:
            now = time.monotonic()
            dt = max(0.0, now - self._last)
            self._last = now

            # refill
            self._tokens = min(float(self.burst), self._tokens + dt * self.qps)

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

            # need to wait
            need = 1.0 - self._tokens
            wait = need / max(self.qps, 1e-6)
        await asyncio.sleep(wait)
        # after sleep, try again (fast path)
        async with self._lock:
            self._tokens = max(0.0, self._tokens - 1.0)
