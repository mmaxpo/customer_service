# app/tools/common/cache.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    value: Any
    expires_at: float | None  # epoch seconds


class MemoryCache:
    """
    Simple in-memory TTL cache.

    Notes:
    - Per-process only (not shared across workers)
    - Good for MCP tool caching + dedupe, not a source of truth.
    """

    def __init__(self, default_ttl_sec: int = 60):
        self.default_ttl_sec = int(default_ttl_sec)
        self._data: dict[str, _Entry] = {}

    def _now(self) -> float:
        return time.time()

    def _is_expired(self, e: _Entry) -> bool:
        return e.expires_at is not None and self._now() >= e.expires_at

    def get(self, key: str) -> Any | None:
        e = self._data.get(key)
        if e is None:
            return None
        if self._is_expired(e):
            self._data.pop(key, None)
            return None
        return e.value

    def set(self, key: str, value: Any, ttl_sec: int | None = None) -> None:
        ttl = self.default_ttl_sec if ttl_sec is None else int(ttl_sec)
        expires_at = None if ttl <= 0 else (self._now() + ttl)
        self._data[key] = _Entry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()