# app/tools/search/providers/tavily.py
import httpx
from app.core.config import settings

class TavilyProvider:
    name = "tavily"

    def is_configured(self) -> bool:
        return bool(getattr(settings, "TAVILY_API_KEY", "") or "")

    async def search(self, q: str, k: int):
        api_key = getattr(settings, "TAVILY_API_KEY", "") or ""
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not set")

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": q, "max_results": k},
            )
        r.raise_for_status()
        data = r.json()

        return [
            {"title": x.get("title",""), "url": x.get("url",""), "snippet": x.get("content","")}
            for x in data.get("results", [])
        ]