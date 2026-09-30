from __future__ import annotations

import uuid
from pydantic import BaseModel, Field
from app.runtime.engine.context import RuntimeContext
from app.runtime.utils.template import get_by_path


class KnowledgeIngestConfig(BaseModel):
    doc_id: str = Field("", description="Doc ID (if empty, auto)")
    text: str = Field("", description="Raw text to ingest")
    from_var: str = Field(
        "",
        description="Read text from vars[from_var] (supports dot paths like web_page.text)",
    )
    source: str = Field("upload")
    filename: str | None = None
    mime_type: str | None = None
    title: str | None = None


class KnowledgeIngestNode:
    """
    Ingest text into the user's knowledge base.

    Reads text from priority order:
        1. config.text
        2. state.vars[from_var]
        3. state.vars["text"]

    Creates doc_id if missing.

    Stores:
        state.vars["doc_id"]
        state.vars["ingest"]

    Output:
        ingest result content.
    """

    async def run(
        self, ctx: RuntimeContext, state: dict, config: KnowledgeIngestConfig
    ) -> dict:
        vars_ = state.get("vars") or {}

        # priority: config.text -> vars[from_var] -> vars.text
        text = (config.text or "").strip()

        if not text and (config.from_var or "").strip():
            v = get_by_path(vars_, config.from_var.strip())

            if isinstance(v, str):
                text = v.strip()
            elif isinstance(v, dict) and isinstance(v.get("text"), str):
                text = v["text"].strip()

        if not text:
            text = str(vars_.get("text") or "").strip()

        if not text:
            raise ValueError(
                "knowledge.ingest: no text provided (config.text, config.from_var, or vars.text)"
            )

        idempotency_key = (
            (getattr(ctx, "node_data", None) or {}).get("_runtime") or {}
        ).get("idempotency_key")
        doc_id = config.doc_id.strip() or (
            f"doc_{idempotency_key}" if idempotency_key else f"doc_{uuid.uuid4().hex}"
        )

        tools = getattr(ctx, "tools", None)
        if tools is None:
            tools = ctx.request.state.tools

        result = await tools.knowledge_ingest.ingest_text(
            db=ctx.db,
            user_id=ctx.user_id,
            doc_id=doc_id,
            text=text,
            source=config.source,
            filename=config.filename,
            mime_type=config.mime_type,
            title=config.title,
            extra_meta={},
        )

        return {
            "output": result.content,
            "patch": {"vars": {"doc_id": doc_id, "ingest": result.artifact}},
            "meta": {"doc_id": doc_id, "idempotency_key": idempotency_key},
            "route": None,
        }
