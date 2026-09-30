from app.runtime.nodes.executor import apply_node_result


def _node_def() -> dict:
    return {
        "id": "capture_context",
        "type": "editable",
        "data": {
            "nodeType": "context.extract",
            "source": "event_payload",
            "path": "session_id",
            "save_as": "customer_chat_session_id",
        },
    }


def test_node_result_updates_last_by_default():
    state = {
        "last": "original customer message",
        "vars": {},
        "results": {},
        "meta": {},
    }

    result = {
        "output": "session-123",
        "patch": {
            "vars": {
                "customer_chat_session_id": "session-123",
            }
        },
    }

    updated = apply_node_result(
        state,
        _node_def(),
        result,
    )

    assert updated["last"] == "session-123"
    assert updated["results"]["capture_context"] == "session-123"
    assert updated["vars"]["customer_chat_session_id"] == "session-123"


def test_node_result_can_preserve_last():
    state = {
        "last": "test-refund rejection-v130d order #1001",
        "vars": {},
        "results": {},
        "meta": {},
    }

    result = {
        "output": "session-123",
        "update_last": False,
        "patch": {
            "vars": {
                "customer_chat_session_id": "session-123",
            }
        },
        "meta": {
            "found": True,
        },
    }

    updated = apply_node_result(
        state,
        _node_def(),
        result,
    )

    assert (
        updated["last"]
        == "test-refund rejection-v130d order #1001"
    )
    assert updated["results"]["capture_context"] == "session-123"
    assert updated["vars"]["customer_chat_session_id"] == "session-123"
    assert updated["meta"]["node_meta_by_id"]["capture_context"] == {
        "found": True
    }


def test_node_result_rejects_invalid_update_last():
    state = {
        "last": "original",
        "vars": {},
        "results": {},
        "meta": {},
    }

    result = {
        "output": "session-123",
        "update_last": "false",
    }

    try:
        apply_node_result(
            state,
            _node_def(),
            result,
        )
    except ValueError as exc:
        assert "non-boolean update_last" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
