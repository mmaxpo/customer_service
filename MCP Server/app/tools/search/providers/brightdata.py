# app/tools/search/providers/brightdata.py
from app.core.config import settings
import httpx

class BrightDataProvider:
    name = "brightdata"

    def is_configured(self) -> bool:
        token = getattr(settings, "BRIGHTDATA_TOKEN", "") or ""
        return bool(token)

    async def search(self, q: str, k: int):
        token = getattr(settings, "BRIGHTDATA_TOKEN", "") or ""
        if not token:
            raise RuntimeError("BRIGHTDATA_TOKEN not set")

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                settings.BRIGHTDATA_URL,
                json={"q": q, "k": k},
                headers={"Authorization": f"Bearer {token}"},
            )
        r.raise_for_status()
        return r.json()["results"]