from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


AgentBackend = Literal["pure"]
AgentPattern = Literal["tool_agent"]


class AgentCustomConfig(BaseModel):
    node_type: Literal["agent.custom"] = "agent.custom"

    name: str | None = None
    save_as: str | None = "agent_result"

    backend: AgentBackend = "pure"
    pattern: AgentPattern = "tool_agent"

    system_prompt: str = "You are a careful AI agent. Use tools when needed."
    instruction: str | None = None

    input_from: Literal["last", "vars"] = "last"
    input_key: str = "input"

    tools: list[str] = Field(default_factory=list)

    max_steps: int = Field(default=8, ge=1, le=50)

    role: Literal["worker", "decision", "final", "final_writer"] = "worker"
    output_mode: Literal["text", "json"] = "text"
    context_keys: list[str] = Field(default_factory=list)

    max_output_chars: int = Field(default=1200, ge=100, le=8000)
    max_output_tokens: int | None = Field(default=None, ge=1, le=4096)
    token_budget_mode: str = Field(default="balanced")

    reasoning_effort: str | None = "low"
    verbosity: str | None = "low"
