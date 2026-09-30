# app/runtime/tools.py
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.tools.common.http import HttpClient
from app.tools.knowledge.ingest.service import KnowledgeIngestService
from app.tools.knowledge.search.service import KnowledgeSearchService
from app.core.providers.llm import (
    build_llm_client,
    build_agent_llm_client,
    LlmClient,
    AgentLLMClientProtocol,
)
from app.tools.mcp.mcp_client import McpSearchClient, McpWebExtractClient


@dataclass
class ToolContainer:
    http: HttpClient
    mcp_search: McpSearchClient
    llm: LlmClient
    web_extract: McpWebExtractClient
    knowledge_ingest: KnowledgeIngestService
    knowledge_search: KnowledgeSearchService
    agent_llm: AgentLLMClientProtocol

    async def aclose(self) -> None:
        await self.mcp_search.aclose()
        await self.web_extract.aclose()


def build_tools() -> ToolContainer:
    http = HttpClient(timeout_sec=20.0, max_retries=2)

    mcp_search = McpSearchClient(
        base_url=settings.MCP_SEARCH_URL,
        api_key=settings.MCP_API_KEY,
    )

    web_extract = McpWebExtractClient(
        base_url=settings.MCP_SEARCH_URL,
        api_key=settings.MCP_API_KEY,
    )

    llm = build_llm_client()
    agent_llm = build_agent_llm_client()
    return ToolContainer(
        llm=llm,
        agent_llm=agent_llm,
        http=http,
        mcp_search=mcp_search,
        web_extract=web_extract,
        knowledge_ingest=KnowledgeIngestService(),
        knowledge_search=KnowledgeSearchService(),
    )
