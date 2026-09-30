import inspect

from app.core.providers.llm import OpenAIResponsesClient


def test_agent_llm_respond_is_async():
    assert inspect.iscoroutinefunction(OpenAIResponsesClient.respond)
