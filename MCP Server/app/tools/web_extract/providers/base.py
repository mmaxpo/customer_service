from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Any


@dataclass
class ExtractResult:
    ok: bool
    url: str
    title: str | None
    text: str
    html: str | None = None
    meta: dict[str, Any] | None = None


class WebExtractProvider(Protocol):
    name: str

    async def extract(
        self,
        *,
        url: str,
        mode: str = "article",
        include_html: bool = False,
        max_chars: int = 200_000,
    ) -> ExtractResult: ...