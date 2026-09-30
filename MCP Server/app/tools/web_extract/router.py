from __future__ import annotations

from app.core.config import settings
from app.tools.common.http import HttpClient
from app.tools.common.cache import MemoryCache
from app.tools.common.ratelimit import RateLimiter

from .providers.simple_http import SimpleHttpProvider
from .providers.base import ExtractResult
from urllib.parse import urlparse

def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""

    # If user provided "www.example.com" or "example.com/path"
    if "://" not in url:
        url = "https://" + url

    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return ""
    return url

class WebExtractRouter:
    def __init__(self):
        self.http = HttpClient(timeout_sec=20.0, max_retries=2)
        self.cache = MemoryCache(default_ttl_sec=120)
        self.limiter = RateLimiter(qps=3.0, burst=6, concurrency=6)

        self.providers = [
            SimpleHttpProvider(self.http),
            # later:
            # ReadabilityProvider(...)
            # PlaywrightProvider(...)
        ]

    async def extract(
        self,
        *,
        url: str,
        mode: str = "article",
        include_html: bool = False,
        max_chars: int = 200_000,
    ) -> ExtractResult:
        url = normalize_url(url)
        if not url:
            # ✅ return a clean artifact, don't 500
            return ExtractResult(
                ok=False,
                url="",
                title=None,
                text="",
                html=None,
                meta={"error": "invalid_url"},
            )
        cache_key = f"web_extract:{mode}:{include_html}:{max_chars}:{url}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        last = None
        async with self.limiter:
            for p in self.providers:
                try:
                    res = await p.extract(
                        url=url,
                        mode=mode,
                        include_html=include_html,
                        max_chars=max_chars,
                    )
                    if res and res.ok:
                        self.cache.set(cache_key, res)
                        return res
                except Exception as e:
                    last = e

        # raise RuntimeError(f"All web_extract providers failed: {last}")
        return ExtractResult(
            ok=False,
            url=url,
            title=None,
            text="",
            html=None,
            meta={"error": f"providers_failed: {repr(last)}"},
        )


router = WebExtractRouter()