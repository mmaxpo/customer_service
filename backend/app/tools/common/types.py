from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Literal

Json = Dict[str, Any]


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = "unknown"


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    content_type: Optional[str]
    final_url: Optional[str]
    text: str
    title: Optional[str] = None
    raw_html: Optional[str] = None
    meta: Optional[Json] = None


@dataclass(frozen=True)
class ToolResult:
    """Stable tool output shape for agents/MCP."""

    content: str
    artifact: Json


class Cache(Protocol):
    async def get(self, key: str) -> Optional[str]: ...
    async def set(self, key: str, value: str, ttl_sec: int) -> None: ...


ProviderName = Literal["google_cse", "searxng", "unknown"]


@dataclass(frozen=True)
class SearchQuery:
    q: str
    k: int = 5
    safesearch: bool = True
    lang: Optional[str] = None
    region: Optional[str] = None
