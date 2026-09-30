from __future__ import annotations

from app.core.config import settings
from app.core.providers.llm.langchain_client import LangChainLlmClient
from app.core.providers.llm.openai_responses import OpenAIResponsesClient


def build_agent_llm_client():
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        return OpenAIResponsesClient(model=settings.OPENAI_MODEL)

    raise ValueError(f"Unsupported agent LLM provider: {settings.LLM_PROVIDER}")


def build_generate_llm_client():
    return LangChainLlmClient()
