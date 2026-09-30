# app/tools/common/http.py
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Optional, Dict, Any

import httpx

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121 Safari/537.36"
)

DEFAULT_ACCEPT = (
    "text/html,text/plain,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
)


@dataclass
class HttpClient:
    timeout_sec: float = 20.0
    max_retries: int = 2
    backoff_base: float = 0.35
    max_bytes: int = 2_500_000  # ~2.5MB cap for safety

    def __post_init__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_sec),
            follow_redirects=True,
            headers={"User-Agent": DEFAULT_UA, "Accept": DEFAULT_ACCEPT},
        )

    async def aclose(self):
        await self._client.aclose()

    async def get_text(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        resp = await self._request("GET", url, headers=headers)

        ct = (resp.headers.get("content-type") or "").lower()

        # allow common textual types
        is_text = (
            "text/" in ct
            or "application/xhtml+xml" in ct
            or "application/xml" in ct
            or "application/json" in ct  # sometimes APIs
        )

        if not is_text:
            # you can choose to return resp and let caller decide,
            # but for fetch+extract we should hard fail.
            raise ValueError(f"Non-text content-type: {ct or 'unknown'}")

        # size guard (best-effort)
        cl = resp.headers.get("content-length")
        try:
            if cl and int(cl) > self.max_bytes:
                raise ValueError(f"Response too large: {cl} bytes")
        except Exception:
            pass

        # if server didn't send content-length, we still cap by truncating resp.text usage elsewhere
        return resp

    async def post_json(
        self,
        url: str,
        json_body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        return await self._request("POST", url, json=json_body, headers=headers)

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._client.request(method, url, **kwargs)

                if resp.status_code in (429, 500, 502, 503, 504):
                    if attempt < self.max_retries:
                        await asyncio.sleep(self._sleep(attempt))
                        continue
                return resp

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exc = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self._sleep(attempt))
                    continue
                raise

        if last_exc:
            raise last_exc
        raise RuntimeError("HTTP request failed")

    def _sleep(self, attempt: int) -> float:
        return (self.backoff_base * (2**attempt)) + random.random() * 0.2
