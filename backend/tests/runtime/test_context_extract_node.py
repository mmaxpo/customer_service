from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.runtime.nodes.builtins.context_extract import (
    ContextExtractConfig,
    ContextExtractNode,
)


@pytest.mark.asyncio
async def test_context_extract_reads_event_payload_into_vars():
    ctx = SimpleNamespace(
        extras={
            "event": {
                "payload": {
                    "session_id": "session-123",
                    "conversation_id": "conversation-456",
                }
            }
        }
    )

    result = await ContextExtractNode().run(
        ctx,
        state={"vars": {}, "last": None},
        config=ContextExtractConfig(
            source="event_payload",
            path="session_id",
            save_as="customer_chat_session_id",
        ),
    )

    assert result["output"] == "session-123"
    assert (
        result["patch"]["vars"]["customer_chat_session_id"]
        == "session-123"
    )
    assert "last" not in result["patch"]
    assert result["meta"] == {
        "source": "event_payload",
        "path": "session_id",
        "save_as": "customer_chat_session_id",
        "found": True,
    }


@pytest.mark.asyncio
async def test_context_extract_supports_nested_paths():
    ctx = SimpleNamespace(
        extras={
            "event": {
                "payload": {
                    "widget": {
                        "workflow_template_id": "template-123",
                    }
                }
            }
        }
    )

    result = await ContextExtractNode().run(
        ctx,
        state={},
        config=ContextExtractConfig(
            source="event_payload",
            path="widget.workflow_template_id",
            save_as="widget_workflow_template_id",
        ),
    )

    assert result["output"] == "template-123"


@pytest.mark.asyncio
async def test_context_extract_required_missing_value_fails():
    ctx = SimpleNamespace(
        extras={
            "event": {
                "payload": {},
            }
        }
    )

    with pytest.raises(
        ValueError,
        match=r"context\.extract could not resolve "
        r"event_payload\.session_id",
    ):
        await ContextExtractNode().run(
            ctx,
            state={},
            config=ContextExtractConfig(
                source="event_payload",
                path="session_id",
                save_as="customer_chat_session_id",
            ),
        )


@pytest.mark.asyncio
async def test_context_extract_optional_missing_value_uses_default():
    ctx = SimpleNamespace(extras={})

    result = await ContextExtractNode().run(
        ctx,
        state={},
        config=ContextExtractConfig(
            source="event_payload",
            path="session_id",
            save_as="customer_chat_session_id",
            required=False,
            default=None,
        ),
    )

    assert result["output"] is None
    assert result["patch"]["vars"]["customer_chat_session_id"] is None
    assert result["meta"]["found"] is False


@pytest.mark.asyncio
async def test_context_extract_can_explicitly_update_last():
    ctx = SimpleNamespace(
        extras={
            "event": {
                "payload": {
                    "session_id": "session-789",
                }
            }
        }
    )

    result = await ContextExtractNode().run(
        ctx,
        state={"vars": {}, "last": "original message"},
        config=ContextExtractConfig(
            source="event_payload",
            path="session_id",
            save_as="customer_chat_session_id",
            update_last=True,
        ),
    )

    assert result["patch"]["last"] == "session-789"
