import pytest

from app.domains.customer_service.services.automation_studio_helpers import (
    diff,
    edit_summary,
    graph_view,
    truncate,
    validate,
)
from app.domains.customer_service.services.automation_studio_json import parse_json


CATALOG = {
    "trigger.message": {"category": "trigger", "risk_level": "safe", "title": "Message"},
    "response": {"category": "action", "risk_level": "safe", "title": "Response"},
    "shopify.order_action": {"category": "action", "risk_level": "sensitive", "title": "Order action"},
}

VALID_GRAPH = {
    "nodes": [
        {"id": "trigger", "data": {"nodeType": "trigger.message"}},
        {"id": "reply", "data": {"nodeType": "response", "label": "Reply"}},
    ],
    "edges": [{"id": "edge", "source": "trigger", "target": "reply"}],
}


def test_validate_accepts_valid_graph_and_reports_missing_approval_or_unknown_type():
    assert validate(VALID_GRAPH, CATALOG) == []

    needs_approval = {
        "nodes": [
            VALID_GRAPH["nodes"][0],
            {"id": "refund", "data": {"nodeType": "shopify.order_action", "label": "Refund"}},
            VALID_GRAPH["nodes"][1],
        ],
        "edges": [
            {"source": "trigger", "target": "refund"},
            {"source": "refund", "target": "reply"},
        ],
    }
    assert any("needs an approval" in error for error in validate(needs_approval, CATALOG))

    unknown = {
        "nodes": [
            VALID_GRAPH["nodes"][0],
            {"id": "mystery", "data": {"nodeType": "unknown.step", "label": "Mystery"}},
            VALID_GRAPH["nodes"][1],
        ],
        "edges": [
            {"source": "trigger", "target": "mystery"},
            {"source": "mystery", "target": "reply"},
        ],
    }
    assert any("workspace does not have" in error for error in validate(unknown, CATALOG))


def test_graph_view_and_diff_are_stable_read_models():
    view = graph_view(VALID_GRAPH, CATALOG)
    assert view["nodes"][1] == {
        "id": "reply",
        "type": "response",
        "label": "Reply",
        "type_title": "Response",
        "category": "action",
        "risk": "safe",
    }
    assert view["edges"] == [{"source": "trigger", "target": "reply", "condition": None}]

    base = {"nodes": [{"id": "old", "data": {"label": "Old"}}, {"id": "same", "data": {}}]}
    proposed = {
        "nodes": [
            {"id": "same", "data": {"label": "Changed"}},
            {"id": "new", "data": {"label": "New"}},
        ]
    }
    assert diff(base, proposed) == {"new": ["new"], "removed": ["old"], "changed": ["same"]}
    assert edit_summary(base, proposed, CATALOG) == [
        {"kind": "new", "text": 'Adds a "New" step.'},
        {"kind": "changed", "text": 'Changes the settings of "Changed".'},
        {"kind": "changed", "text": 'Removes the "Old" step.'},
        {"kind": "same", "text": "Everything else, including your workspace rules, stays the same."},
    ]


def test_parse_json_accepts_plain_and_fenced_objects_and_rejects_missing_json():
    assert parse_json('{"ok": true}') == {"ok": True}
    assert parse_json('```json\n{"ok": true}\n```') == {"ok": True}
    with pytest.raises(ValueError, match="no JSON object"):
        parse_json("not JSON")


def test_truncate_preserves_short_values_and_caps_long_values():
    assert truncate(None) is None
    assert truncate("short") == "short"
    long_value = truncate("x" * 1300)
    assert len(long_value) == 1201
    assert long_value.endswith("…")
