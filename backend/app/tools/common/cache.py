from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class MemoryCache:
    """Tiny in-memory cache (good enough for dev; swap with Redis later)."""

    default_ttl_sec: int = 300

    def __post_init__(self):
        self._data: Dict[str, str] = {}
        self._exp: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            exp = self._exp.get(key)
            if exp is not None and exp < time.time():
                self._data.pop(key, None)
                self._exp.pop(key, None)
                return None
            return self._data.get(key)

    async def set(self, key: str, value: str, ttl_sec: int | None = None) -> None:
        ttl = int(ttl_sec or self.default_ttl_sec)
        async with self._lock:
            self._data[key] = value
            self._exp[key] = time.time() + ttl
