from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.agents_runtime.tools.registry import ToolRegistry
from app.agents_runtime.tools.schemas import AgentTool, ToolRiskLevel
from app.core.session import SessionLocal


def calculator(expression: str) -> dict:
    allowed_chars = set("0123456789+-*/(). ")

    if not set(expression).issubset(allowed_chars):
        raise ValueError("Invalid calculator expression")

    return {"result": eval(expression)}








def _tool_result_to_agent(result: Any) -> dict[str, Any]:

    content = getattr(result, "content", None)

    artifact = getattr(result, "artifact", None)

    if content is not None or artifact is not None:
        return {
            "content": content,
            "artifact": artifact,
        }

    return {"content": str(result), "artifact": result}


def _extract_math_expression(text: str) -> str:

    match = re.search(r"[-+*/().\d\s]+", text)

    return match.group(0).strip() if match else text


def build_builtin_tool_registry(
    *, tools: Any | None = None, user_id: Any | None = None
) -> ToolRegistry:

    registry = ToolRegistry()

    async def calculator(expression: str) -> dict[str, Any]:

        safe_expression = _extract_math_expression(expression)

        if not re.fullmatch(r"[-+*/().\d\s]+", safe_expression):
            raise ValueError("Only basic arithmetic expressions are allowed.")

        result = eval(safe_expression, {"__builtins__": {}}, {})

        return {"result": result}

    registry.register(
        AgentTool(
            name="calculator",
            description="Evaluate basic arithmetic expressions. Use for math calculations.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Arithmetic expression, for example: 25 * 19 + 7",
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
            function=calculator,
            risk_level=ToolRiskLevel.SAFE,
        )
    )


    async def knowledge_search(query: str, k: int = 5) -> dict[str, Any]:

        if tools is None or not hasattr(tools, "knowledge_search"):
            raise RuntimeError("knowledge_search service is not available.")

        if user_id is None:
            raise RuntimeError("knowledge_search requires authenticated user_id.")

        async with SessionLocal() as db:
            result = await tools.knowledge_search.search(
                db=db,
                user_id=UUID(str(user_id)),
                query=query,
                k=k,
            )

        return _tool_result_to_agent(result)

    registry.register(
        AgentTool(
            name="knowledge_search",
            description="Search the user's knowledge base for policies, FAQs, product docs, and support content.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query.",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of results to retrieve.",
                        "default": 5,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            function=knowledge_search,
            risk_level=ToolRiskLevel.SAFE,
        )
    )

    async def web_search(q: str, k: int = 5) -> dict[str, Any]:

        if tools is None or not hasattr(tools, "mcp_search"):
            raise RuntimeError("mcp_search service is not available.")

        result = await tools.mcp_search.search(q=q, k=k)

        return _tool_result_to_agent(result)

    registry.register(
        AgentTool(
            name="web_search",
            description="Search the web using the configured MCP search service.",
            parameters={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Search query.",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of results.",
                        "default": 5,
                    },
                },
                "required": ["q"],
                "additionalProperties": False,
            },
            function=web_search,
            risk_level=ToolRiskLevel.SAFE,
        )
    )

    async def web_fetch_extract(
        url: str,
        mode: str = "article",
        include_html: bool = False,
        max_chars: int = 200000,
    ) -> dict[str, Any]:

        if tools is None or not hasattr(tools, "web_extract"):
            raise RuntimeError("web_extract service is not available.")

        result = await tools.web_extract.extract(
            url=url,
            mode=mode,
            include_html=include_html,
            max_chars=max_chars,
        )

        return _tool_result_to_agent(result)

    registry.register(
        AgentTool(
            name="web_fetch_extract",
            description="Fetch a URL and extract readable page content using the configured MCP extract service.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch.",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Extraction mode.",
                        "default": "article",
                    },
                    "include_html": {
                        "type": "boolean",
                        "default": False,
                    },
                    "max_chars": {
                        "type": "integer",
                        "default": 200000,
                    },
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            function=web_fetch_extract,
            risk_level=ToolRiskLevel.SAFE,
        )
    )


    return registry
