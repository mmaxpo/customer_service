from __future__ import annotations

from dataclasses import dataclass

from app.agents_runtime.usage.schemas import AgentRunUsage


class UsageBudgetExceeded(Exception):
    pass


@dataclass(slots=True)
class UsageBudget:
    max_total_tokens: int | None = None
    max_llm_calls: int | None = None
    max_tool_calls: int | None = None

    def check(self, usage: AgentRunUsage) -> None:
        if (
            self.max_total_tokens is not None
            and usage.total_tokens > self.max_total_tokens
        ):
            raise UsageBudgetExceeded(
                f"Token budget exceeded: {usage.total_tokens} > {self.max_total_tokens}"
            )

        if self.max_llm_calls is not None and usage.llm_calls > self.max_llm_calls:
            raise UsageBudgetExceeded(
                f"LLM call budget exceeded: {usage.llm_calls} > {self.max_llm_calls}"
            )

        if (
            self.max_tool_calls is not None
            and usage.tool_calls > self.max_tool_calls
        ):
            raise UsageBudgetExceeded(
                f"Tool call budget exceeded: {usage.tool_calls} > "
                f"{self.max_tool_calls}"
            )
