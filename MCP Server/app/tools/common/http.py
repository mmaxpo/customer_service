# app/tools/common/http.py
from __future__ import annotations

import httpx


class HttpClient:
    def __init__(self, timeout_sec: float = 20.0, max_retries: int = 0):
        self.timeout_sec = float(timeout_sec)
        self.max_retries = int(max_retries)

        # Keep one AsyncClient for connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_sec),
            follow_redirects=True,  # ✅ IMPORTANT
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
        )

    async def get(self, url: str, **kw) -> httpx.Response:
        return await self._request("GET", url, **kw)

    async def post(self, url: str, **kw) -> httpx.Response:
        return await self._request("POST", url, **kw)

    async def _request(self, method: str, url: str, **kw) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                r = await self.client.request(method, url, **kw)
                r.raise_for_status()
                return r
            except Exception as e:
                last_exc = e
                if attempt >= self.max_retries:
                    raise
        raise last_exc  # for type checkers

    async def aclose(self) -> None:
        await self.client.aclose()


# ✅ shared singleton (so existing imports keep working)
http = HttpClient()