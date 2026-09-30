from __future__ import annotations

from typing import Any, Protocol


class AgentLLMClientProtocol(Protocol):
    async def respond(
        self,
        *,
        input_items: list[Any],
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        verbosity: str | None = None,
    ) -> Any: ...


class GenerateLLMClientProtocol(Protocol):
    async def generate(
        self,
        *,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ): ...
