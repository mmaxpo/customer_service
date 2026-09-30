# app/tools/mcp/mcp_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import httpx


@dataclass
class McpToolResult:
    content: str
    artifact: Dict[str, Any]


class McpSearchClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout_sec: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout_sec,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, q: str, k: int) -> McpToolResult:
        r = await self._client.post(
            "/mcp/search",
            headers={"X-API-Key": self.api_key},
            json={"query": q, "k": k},
        )
        r.raise_for_status()
        data = r.json()

        artifact = {"ok": True, "query": q, "results": data.get("results", [])}
        return McpToolResult(content="OK", artifact=artifact)


class McpWebExtractClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout_sec: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout_sec,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def extract(
        self,
        url: str,
        *,
        mode: str = "article",
        include_html: bool = False,
        max_chars: int = 200_000,
    ) -> McpToolResult:
        r = await self._client.post(
            "/mcp/extract",
            headers={"X-API-Key": self.api_key},
            json={
                "url": url,
                "mode": mode,
                "include_html": include_html,
                "max_chars": max_chars,
            },
        )
        r.raise_for_status()
        data = r.json()
        content = (data.get("text") or "").strip()
        return McpToolResult(content=content, artifact=data)
