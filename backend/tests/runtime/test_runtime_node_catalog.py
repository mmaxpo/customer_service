from __future__ import annotations

from app.runtime.nodes.registry import list_registered_nodes


def test_node_catalog_lists_registered_nodes():
    items = list_registered_nodes()
    assert isinstance(items, list)
    assert len(items) > 0

    by_type = {x["node_type"]: x for x in items}
    assert "trigger.message" in by_type
    assert "response" in by_type

    # UI fields exist
    t = by_type["trigger.message"]
    assert isinstance(t.get("title"), str) and t["title"]
    assert isinstance(t.get("group"), str) and t["group"]
    assert isinstance(t.get("icon"), str) and t["icon"]
    assert isinstance(t.get("default_config"), dict)

    # schema shape
    s = t["schema"]
    assert isinstance(s, dict)
    # pydantic json schema usually object
    assert s.get("type") == "object"

    dc = t["default_config"]
    assert (
        dc.get("nodeType") == "trigger.message"
        or dc.get("node_type") == "trigger.message"
    )
