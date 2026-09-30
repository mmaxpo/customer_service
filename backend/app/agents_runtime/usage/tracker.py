from __future__ import annotations

from typing import Any

from app.agents_runtime.usage.schemas import AgentRunUsage, TokenUsage


def extract_token_usage(response: Any) -> TokenUsage:
    usage = getattr(response, "usage", None)

    if usage is None:
        return TokenUsage()

    input_tokens = (
        getattr(usage, "input_tokens", None)
        or getattr(usage, "prompt_tokens", None)
        or 0
    )

    output_tokens = (
        getattr(usage, "output_tokens", None)
        or getattr(usage, "completion_tokens", None)
        or 0
    )

    total_tokens = getattr(usage, "total_tokens", None) or input_tokens + output_tokens

    return TokenUsage(
        input_tokens=int(input_tokens or 0),
        output_tokens=int(output_tokens or 0),
        total_tokens=int(total_tokens or 0),
    )


def extract_model_name(response: Any) -> str | None:
    model = getattr(response, "model", None)

    if model:
        return str(model)

    return None


class UsageTracker:
    def __init__(self, agent_run_id: str) -> None:
        self.usage = AgentRunUsage(agent_run_id=agent_run_id)

    def record_llm_response(self, response: Any) -> TokenUsage:
        token_usage = extract_token_usage(response)

        model = extract_model_name(response)
        if model and self.usage.model is None:
            self.usage.model = model

        self.usage.add(token_usage)

        return token_usage

    def record_tool_call(self) -> None:
        self.usage.add_tool_call()
