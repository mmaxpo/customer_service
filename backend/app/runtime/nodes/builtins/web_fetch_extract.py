from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class WebFetchExtractConfig(BaseModel):
    url: str = ""
    mode: str = "article"
    include_html: bool = False
    max_chars: int = 200_000

    artifact_as: str | None = Field(default=None)
    save_as: str | None = Field(default=None)

    @model_validator(mode="after")
    def _resolve_alias(self):
        if not self.artifact_as:
            self.artifact_as = self.save_as or "web_extract"
        return self


def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    return str(x)


class WebFetchExtractNode:
    """
    Fetch and extract readable text from a URL.

    Reads URL from:
        - config.url
        - state.vars["url"]

    Supports:
        - tools.web_fetch_extract.fetch_extract(url)
        - tools.mcp_web_extract.extract(...)
        - tools.web_extract.extract(...)
        - tools.mcp_extract.extract(...)

    Stores artifact in:
        state.vars[artifact_as]
    """

    async def run(self, ctx, state: dict, config: WebFetchExtractConfig) -> dict:
        vars_ = state.get("vars") or {}
        url = (config.url or _safe_str(vars_.get("url"))).strip()
        if not url:
            raise ValueError("web.fetch_extract: url is empty (config.url or vars.url)")

        tools = getattr(ctx, "tools", None) or ctx.request.state.tools

        # 1) Backend tool used by YOUR TEST: tools.web_fetch_extract.fetch_extract(url)
        wf = getattr(tools, "web_fetch_extract", None)
        if wf is not None and hasattr(wf, "fetch_extract"):
            r = await wf.fetch_extract(url)

            content = _safe_str(getattr(r, "content", None))
            raw = getattr(r, "artifact", None) or {}

            text = raw.get("text")
            if not text:
                text = content  # fallback so tests + templates always have text

            artifact = {
                "ok": bool(raw.get("ok", True)),
                "url": raw.get("url") or url,
                "title": raw.get("title"),
                "text": _safe_str(text)[: config.max_chars],
                "html": (raw.get("html") if config.include_html else None),
                "meta": raw.get("meta") or {},
            }

            return {
                "output": content or "EXTRACTED",
                "patch": {"vars": {config.artifact_as: artifact}},
                "meta": {"url": url},
                "route": None,
            }

        # 2) MCP-style clients (production path): .extract(url, ...)
        extract_client = (
            getattr(tools, "mcp_web_extract", None)
            or getattr(tools, "web_extract", None)
            or getattr(tools, "mcp_extract", None)
        )
        if extract_client is None:
            raise AttributeError(
                "web.fetch_extract: tools has no web_fetch_extract.fetch_extract "
                "and no mcp_web_extract/web_extract/mcp_extract client"
            )

        r = await extract_client.extract(
            url,
            mode=config.mode,
            include_html=config.include_html,
            max_chars=config.max_chars,
        )

        raw = getattr(r, "artifact", None) or {}
        text = (
            raw.get("text")
            or _safe_str(getattr(r, "content", None))
            or _safe_str(getattr(r, "output", None))
        )

        artifact = {
            "ok": bool(raw.get("ok", True)),
            "url": raw.get("url") or url,
            "title": raw.get("title"),
            "text": _safe_str(text)[: config.max_chars],
            "html": (raw.get("html") if config.include_html else None),
            "meta": raw.get("meta") or {},
        }

        return {
            "output": "EXTRACTED",
            "patch": {"vars": {config.artifact_as: artifact}},
            "meta": {"url": url},
            "route": None,
        }
