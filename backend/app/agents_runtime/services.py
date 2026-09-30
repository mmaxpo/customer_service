from __future__ import annotations

from dataclasses import dataclass

from app.agents_runtime.events import AgentEventStream, PostgresAgentEventStore
from app.core.providers.llm import build_agent_llm_client
from app.agents_runtime.runner import AgentRunner
from app.agents_runtime.state import PostgresAgentStateStore
from app.agents_runtime.tools import ToolRegistry, build_builtin_tool_registry
from app.core.session import SessionLocal


@dataclass
class AgentRuntimeServices:
    tool_registry: ToolRegistry
    event_store: PostgresAgentEventStore
    event_stream: AgentEventStream
    state_store: PostgresAgentStateStore
    runner: AgentRunner


def build_agent_runtime_services() -> AgentRuntimeServices:
    tool_registry = build_builtin_tool_registry()
    event_store = PostgresAgentEventStore(SessionLocal)
    event_stream = AgentEventStream()
    state_store = PostgresAgentStateStore(SessionLocal)

    try:
        llm = build_agent_llm_client()
    except Exception as exc:
        raise RuntimeError(
            "OPENAI_API_KEY is required for AgentRuntimeServices"
        ) from exc

    runner = AgentRunner(
        llm=llm,
        tool_registry=tool_registry,
        event_store=event_store,
        event_stream=event_stream,
        state_store=state_store,
    )

    return AgentRuntimeServices(
        tool_registry=tool_registry,
        event_store=event_store,
        event_stream=event_stream,
        state_store=state_store,
        runner=runner,
    )
