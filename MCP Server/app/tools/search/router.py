from app.core.config import settings

from .providers.brave import BraveProvider
from .providers.brightdata import BrightDataProvider
from .providers.searxng import SearxProvider
from .providers.tavily import TavilyProvider


class SearchRouter:
    def __init__(self):
        self.providers = [
            TavilyProvider(),
            SearxProvider(settings.SEARXNG_URL),
            BraveProvider(),
            BrightDataProvider(),
        ]

    async def search(self, q: str, k: int):
        last = None

        for p in self.providers:
            # ✅ skip providers that are not configured
            if hasattr(p, "is_configured") and not p.is_configured():
                continue

            try:
                return await p.search(q, k)
            except Exception as e:
                last = e

        raise RuntimeError(f"All providers failed: {last}")


router = SearchRouter()
