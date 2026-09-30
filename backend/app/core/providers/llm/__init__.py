from app.core.providers.llm.factory import (
    build_agent_llm_client,
    build_generate_llm_client,
)
from app.core.providers.llm.langchain_client import (
    LangChainLlmClient,
    get_langchain_llm,
)
from app.core.providers.llm.openai_responses import OpenAIResponsesClient
from app.core.providers.llm.protocols import (
    AgentLLMClientProtocol,
    GenerateLLMClientProtocol,
)
from app.core.providers.llm.schemas import LlmResult
from app.core.providers.llm.resilience import (
    LLMCircuitBreaker,
    LLMCircuitOpenError,
    LLMProviderError,
    LLMProviderRequestError,
    LLMProviderTransientError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResilienceMetrics,
    LLMRetryPolicy,
    classify_openai_error,
    execute_openai_with_resilience,
    is_llm_provider_failure_message,
    llm_circuit_breaker,
    llm_resilience_metrics,
)

# Backward-compatible names used by older app code.
get_llm = get_langchain_llm
build_llm_client = build_generate_llm_client
LlmClient = GenerateLLMClientProtocol

__all__ = [
    "AgentLLMClientProtocol",
    "GenerateLLMClientProtocol",
    "LangChainLlmClient",
    "LlmClient",
    "LlmResult",
    "OpenAIResponsesClient",
    "LLMCircuitBreaker",
    "LLMCircuitOpenError",
    "LLMProviderError",
    "LLMProviderRequestError",
    "LLMProviderTransientError",
    "LLMQuotaExceededError",
    "LLMRateLimitError",
    "LLMResilienceMetrics",
    "LLMRetryPolicy",
    "build_agent_llm_client",
    "build_generate_llm_client",
    "build_llm_client",
    "get_langchain_llm",
    "get_llm",
    "classify_openai_error",
    "execute_openai_with_resilience",
    "is_llm_provider_failure_message",
    "llm_circuit_breaker",
    "llm_resilience_metrics",
]
