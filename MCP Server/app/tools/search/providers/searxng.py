from app.tools.common.http import http


class SearxProvider:
    name = "searxng"

    def __init__(self, base_url: str):
        self.url = base_url

    async def search(self, q: str, k: int):

        r = await http.get(
            f"{self.url}/search",
            params={
                "q": q,
                "format": "json",
                "limit": k,
            },
        )

        data = r.json()

        return [
            {
                "title": x["title"],
                "url": x["url"],
                "snippet": x.get("content"),
            }
            for x in data.get("results", [])
        ]
