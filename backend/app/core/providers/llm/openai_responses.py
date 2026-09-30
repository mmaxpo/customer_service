from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.providers.llm.resilience import (
    LLMCircuitBreaker,
    LLMRetryPolicy,
    execute_openai_with_resilience,
)


class OpenAIResponsesClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: Any | None = None,
        retry_policy: LLMRetryPolicy | None = None,
        circuit_breaker: LLMCircuitBreaker | None = None,
    ) -> None:
        self.client = client or AsyncOpenAI(
            api_key=api_key or settings.OPENAI_API_KEY,
            max_retries=0,
        )
        self.model = model or settings.OPENAI_MODEL
        self.retry_policy = retry_policy or LLMRetryPolicy.from_settings(settings)
        self.circuit_breaker = circuit_breaker

    def _supports_reasoning_effort(self) -> bool:
        """
        Return whether this OpenAI model accepts Responses API
        reasoning-effort configuration.

        Provider/model feature compatibility belongs here rather than in
        the generic agent runtime.
        """

        model = (self.model or "").lower()

        return (
            model.startswith("gpt-5")
            or model.startswith("o1")
            or model.startswith("o3")
            or model.startswith("o4")
        )

    def _supports_verbosity(self) -> bool:
        """
        Return whether to send OpenAI response-verbosity tuning.

        Keep optional tuning conservative: unsupported models should
        receive a normal Responses API request rather than fail because
        of an optimization hint.
        """

        model = (self.model or "").lower()

        return model.startswith("gpt-5")

    async def respond(
        self,
        *,
        input_items: list[Any],
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        verbosity: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": input_items,
        }

        if tools:
            payload["tools"] = tools

        if system_prompt:
            payload["instructions"] = system_prompt

        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens

        if reasoning_effort and self._supports_reasoning_effort():
            payload["reasoning"] = {"effort": reasoning_effort}

        if verbosity and self._supports_verbosity():
            payload["text"] = {"verbosity": verbosity}

        resilience_kwargs = {
            "policy": self.retry_policy,
        }
        if self.circuit_breaker is not None:
            resilience_kwargs["breaker"] = self.circuit_breaker

        return await execute_openai_with_resilience(
            lambda: self.client.responses.create(**payload),
            **resilience_kwargs,
        )
