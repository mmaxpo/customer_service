from __future__ import annotations

from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, MessagesState
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from app.core.config import settings
from app.core.providers.llm.resilience import (
    LLMRetryPolicy,
    execute_openai_with_resilience,
)


SYSTEM = """
You are a support agent for a shop.
For policy/refund/shipping/return questions:
1) ALWAYS call knowledge_search first.
2) Answer ONLY from tool results.
If nothing found, say: "I couldn't find it in the knowledge base."
"""


@dataclass
class Context:
    user_id: str  # we will pass current_user.id here


async def inject_user_id_header(request: MCPToolCallRequest, handler):
    # ✅ get user_id from LangGraph runtime config
    user_id = (request.runtime.config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        # return a safe tool result instead of crashing
        modified = request.override(args={**request.args, "headers": {"X-User-Id": ""}})
        return await handler(modified)

    modified = request.override(
        args={**request.args, "headers": {"X-User-Id": str(user_id)}},
    )
    return await handler(modified)


async def build_agent_graph_mcp(checkpointer):
    """connect to MCP server"""
    client = MultiServerMCPClient(
        {
            "knowledge": {
                "transport": "http",
                "url": "http://127.0.0.1:8001/mcp",
            }
        },
        tool_interceptors=[inject_user_id_header],
    )

    tools = await client.get_tools()  # loads MCP tools as LangChain tools

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        api_key=settings.OPENAI_API_KEY,
        max_retries=0,
    )
    llm_with_tools = llm.bind_tools(tools)

    tool_node = ToolNode(tools)

    async def assistant(state: MessagesState):
        msgs = [SystemMessage(content=SYSTEM), *state["messages"]]
        resp = await execute_openai_with_resilience(
            lambda: llm_with_tools.ainvoke(msgs),
            policy=LLMRetryPolicy.from_settings(settings),
        )
        return {"messages": [resp]}

    g = StateGraph(MessagesState)
    g.add_node("assistant", assistant)
    g.add_node("tools", tool_node)

    g.add_edge(START, "assistant")
    g.add_conditional_edges("assistant", tools_condition)
    g.add_edge("tools", "assistant")

    return g.compile(checkpointer=checkpointer)
