from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.providers.llm.schemas import LlmResult
from app.core.providers.llm.resilience import (
    LLMRetryPolicy,
    execute_openai_with_resilience,
)


@lru_cache(maxsize=8)
def get_langchain_llm(provider: str | None = None, model: str | None = None) -> Any:
    provider = (provider or settings.LLM_PROVIDER).lower()

    if provider == "openai":
        return ChatOpenAI(
            model=(model or settings.OPENAI_MODEL),
            api_key=settings.OPENAI_API_KEY,
            max_retries=0,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


class LangChainLlmClient:
    def _model_requires_default_temperature(self, model: str | None) -> bool:
        name = (model or settings.OPENAI_MODEL or "").lower()
        return name.startswith("o") or "reasoning" in name or name.startswith("gpt-5")

    async def generate(
        self,
        *,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LlmResult:
        llm = get_langchain_llm(model=model)

        if temperature is not None and not self._model_requires_default_temperature(
            model
        ):
            llm = llm.bind(temperature=temperature)
        if max_tokens is not None:
            llm = llm.bind(max_tokens=max_tokens)

        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        resp = await execute_openai_with_resilience(
            lambda: llm.ainvoke(messages),
            policy=LLMRetryPolicy.from_settings(settings),
        )

        text = getattr(resp, "content", None)
        if isinstance(text, list):
            text = "".join(str(x) for x in text)

        usage = getattr(resp, "usage_metadata", None) or getattr(
            resp, "response_metadata", None
        )

        return LlmResult(
            text=str(text or ""),
            model=getattr(llm, "model_name", None) or model,
            usage=usage if isinstance(usage, dict) else None,
        )
