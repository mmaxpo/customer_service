from __future__ import annotations

import re
from html import unescape

from app.tools.common.http import HttpClient
from .base import ExtractResult


# Remove whole blocks first (less garbage)
_BLOCK_RE = re.compile(
    r"(?is)<(script|style|noscript|svg|iframe|canvas)\b[^>]*>.*?</\1>"
)
_COMMENT_RE = re.compile(r"(?s)<!--.*?-->")
_TAG_RE = re.compile(r"(?s)<[^>]+>")
_WS_RE = re.compile(r"\s+")

_TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
_H1_RE = re.compile(r"(?is)<h1[^>]*>(.*?)</h1>")


def _clean_html(html: str) -> str:
    html = _COMMENT_RE.sub(" ", html)
    html = _BLOCK_RE.sub(" ", html)
    return html


def _strip_html(html: str) -> str:
    txt = unescape(_TAG_RE.sub(" ", html))
    txt = _WS_RE.sub(" ", txt).strip()
    return txt


def _extract_title(html: str) -> str | None:
    m = _TITLE_RE.search(html)
    if m:
        t = unescape(m.group(1))
        t = _WS_RE.sub(" ", t).strip()
        if t:
            return t

    # fallback: h1
    m = _H1_RE.search(html)
    if m:
        t = unescape(m.group(1))
        t = _WS_RE.sub(" ", t).strip()
        if t:
            return t

    return None


class SimpleHttpProvider:
    name = "simple_http"

    def __init__(self, http: HttpClient):
        self.http = http

    async def extract(
        self,
        *,
        url: str,
        mode: str = "article",
        include_html: bool = False,
        max_chars: int = 200_000,
    ) -> ExtractResult:
        # IMPORTANT: don't override your HttpClient UA with a weak one
        # Let HttpClient default headers handle UA.
        r = await self.http.get(url)

        html = r.text or ""
        cleaned = _clean_html(html)

        title = _extract_title(cleaned)
        text = _strip_html(cleaned)

        if max_chars and len(text) > max_chars:
            text = text[:max_chars]

        return ExtractResult(
            ok=True,
            url=url,
            title=title,
            text=text,
            html=html if include_html else None,
            meta={"provider": self.name, "mode": mode},
        )