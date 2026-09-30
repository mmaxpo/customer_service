from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class WebSearchConfig(BaseModel):
    query: str = ""
    k: int = 5

    artifact_as: str | None = Field(default=None)
    save_as: str | None = Field(default=None)

    @model_validator(mode="after")
    def _resolve_alias(self):
        if not self.artifact_as:
            self.artifact_as = self.save_as or "web_search"
        return self


def _normalize_item(item: dict) -> dict:
    url = item.get("url") or item.get("link") or ""
    link = item.get("link") or item.get("url") or ""
    return {
        "title": item.get("title", "") or "",
        "url": url,
        "link": link,
        "snippet": item.get("snippet") or item.get("content") or "",
        **item,  # keep extras
    }


class WebSearchNode:
    """
    Web search node.

    Reads query from:
        - config.query
        - state.vars["query"]

    Uses tools.mcp_search or tools.web_search.

    Stores normalized search artifact in:
        state.vars[artifact_as]

    Artifact shape:
        {
            "ok": bool,
            "query": str,
            "results": [...]
        }
    """

    async def run(self, ctx, state: dict, config: WebSearchConfig) -> dict:
        vars_ = state.get("vars") or {}

        q = (config.query or str(vars_.get("query") or "")).strip()
        if not q:
            raise ValueError("web.search: query is empty (config.query or vars.query)")

        tools = getattr(ctx, "tools", None) or ctx.request.state.tools
        client = getattr(tools, "mcp_search", None) or getattr(
            tools, "web_search", None
        )
        if client is None:
            raise AttributeError(
                "web.search: tools has no mcp_search/web_search client"
            )

        # MCP returns a result object; tests may return list[dict]
        resp = await client.search(q, config.k)

        raw_artifact = getattr(resp, "artifact", None) or {}
        raw_results = raw_artifact.get("results")
        if raw_results is None:
            raw_results = resp if isinstance(resp, list) else []

        norm_results: list[dict] = []
        for item in raw_results:
            if isinstance(item, dict):
                norm_results.append(_normalize_item(item))
            else:
                norm_results.append(
                    {"title": str(item), "url": "", "link": "", "snippet": ""}
                )

        artifact = {
            "ok": bool(raw_artifact.get("ok", True)),
            "query": q,
            "results": norm_results,
        }

        return {
            "output": "RESULT",
            "patch": {"vars": {config.artifact_as: artifact}},
            "meta": {"k": config.k},
            "route": None,
        }
