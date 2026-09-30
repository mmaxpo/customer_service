from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeSearchConfig(BaseModel):
    query: str = Field("", description="Query (or vars.query)")
    k: int = Field(8, ge=1, le=20)
    artifact_as: str = Field("kb_hits", description="vars key to store hits list")


class KnowledgeSearchNode:
    """
    Search the user's knowledge base.

    Reads query from:
        - config.query
        - state.vars["query"]

    Stores hits in:
        state.vars[artifact_as]

    Output:
        result.content

    Example:
        config.artifact_as = "kb_hits"
        patch = {"vars": {"kb_hits": [...]}}
    """

    async def run(self, ctx, state: dict, config: KnowledgeSearchConfig) -> dict:
        vars_ = state.get("vars") or {}

        query = config.query or str(vars_.get("query") or "")
        if not query.strip():
            raise ValueError("kb.search: query is empty (config.query or vars.query)")

        tools = ctx.request.state.tools
        result = await tools.knowledge_search.search(
            db=ctx.db,
            user_id=ctx.user_id,
            query=query,
            k=config.k,
        )

        hits = (result.artifact or {}).get("hits", [])
        patch = {"vars": {config.artifact_as: hits}}

        return {
            "output": result.content,
            "patch": patch,
            "meta": {"k": config.k, "hits": len(hits)},
            "route": None,
        }
