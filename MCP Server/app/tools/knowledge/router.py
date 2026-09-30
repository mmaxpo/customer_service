from __future__ import annotations

import uuid
from typing import Dict, Optional

from fastmcp import FastMCP

from app.tools.knowledge.service import KnowledgeService


def register_knowledge_tools(
    mcp: FastMCP,
    service: KnowledgeService,
):
    def _get_user_id(headers: Dict[str, str]) -> uuid.UUID:
        raw = headers.get("x-user-id") or headers.get("X-User-Id")
        if not raw:
            raise PermissionError("Missing X-User-Id")

        return uuid.UUID(str(raw))

    @mcp.tool()
    async def knowledge_search(
        query: str,
        k: int = 6,
        headers: Optional[dict] = None,
    ):
        headers = headers or {}
        uid = _get_user_id(headers)

        return await service.search(uid, query, k)

    @mcp.tool()
    async def knowledge_list_docs(
        headers: Optional[dict] = None,
    ):
        headers = headers or {}
        uid = _get_user_id(headers)

        return await service.list_docs(uid)

    @mcp.tool()
    async def knowledge_delete_doc(
        doc_id: str,
        headers: Optional[dict] = None,
    ):
        headers = headers or {}
        uid = _get_user_id(headers)

        return await service.delete_doc(uid, doc_id)