from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.providers.llm import OpenAIResponsesClient


def _client(model: str) -> OpenAIResponsesClient:
    client = OpenAIResponsesClient(
        api_key="test-key",
        model=model,
    )

    client.client.responses.create = AsyncMock(
        return_value=object()
    )

    return client


@pytest.mark.asyncio
async def test_gpt_4_1_omits_unsupported_agent_tuning():
    client = _client(
        "gpt-4.1-mini-2025-04-14"
    )

    await client.respond(
        input_items=[
            {
                "role": "user",
                "content": "hello",
            }
        ],
        tools=[],
        max_output_tokens=100,
        reasoning_effort="low",
        verbosity="low",
    )

    payload = (
        client.client.responses.create.await_args.kwargs
    )

    assert payload["model"] == (
        "gpt-4.1-mini-2025-04-14"
    )
    assert payload["max_output_tokens"] == 100
    assert "reasoning" not in payload
    assert "text" not in payload


@pytest.mark.asyncio
async def test_gpt_5_keeps_reasoning_and_verbosity_tuning():
    client = _client(
        "gpt-5-mini"
    )

    await client.respond(
        input_items=[
            {
                "role": "user",
                "content": "hello",
            }
        ],
        tools=[],
        reasoning_effort="low",
        verbosity="low",
    )

    payload = (
        client.client.responses.create.await_args.kwargs
    )

    assert payload["reasoning"] == {
        "effort": "low"
    }
    assert payload["text"] == {
        "verbosity": "low"
    }


@pytest.mark.asyncio
async def test_o_series_keeps_reasoning_but_omits_verbosity():
    client = _client(
        "o4-mini"
    )

    await client.respond(
        input_items=[
            {
                "role": "user",
                "content": "hello",
            }
        ],
        tools=[],
        reasoning_effort="low",
        verbosity="low",
    )

    payload = (
        client.client.responses.create.await_args.kwargs
    )

    assert payload["reasoning"] == {
        "effort": "low"
    }
    assert "text" not in payload
