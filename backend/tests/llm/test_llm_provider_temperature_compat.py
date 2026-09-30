from app.core.providers.llm.langchain_client import LangChainLlmClient


def test_reasoning_models_do_not_bind_custom_temperature():
    client = LangChainLlmClient()
    assert client._model_requires_default_temperature("gpt-5.5-thinking") is True
    assert client._model_requires_default_temperature("o3") is True


def test_normal_chat_models_can_bind_temperature():
    client = LangChainLlmClient()
    assert client._model_requires_default_temperature("gpt-4o-mini") is False
