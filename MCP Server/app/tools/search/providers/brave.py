# app/tools/search/providers/brave.py
from app.core.config import settings
import httpx

class BraveProvider:
    name = "brave"

    def is_configured(self) -> bool:
        return bool(getattr(settings, "BRAVE_API_KEY", "") or "")

    async def search(self, q: str, k: int):
        api_key = getattr(settings, "BRAVE_API_KEY", "") or ""
        if not api_key:
            raise RuntimeError("BRAVE_API_KEY not set")

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": q, "count": k},
                headers={"X-Subscription-Token": api_key},  # brave uses this header
            )
        r.raise_for_status()
        data = r.json()
        # map results...