from app.tcos.capabilities.catalog import list_capability_catalog


def test_list_capability_catalog_returns_frontend_ready_items():
    items = list_capability_catalog()

    assert items
    first = items[0]

    assert "id" in first
    assert "title" in first
    assert "description" in first
    assert "domain" in first
    assert "category" in first
    assert "source" in first
    assert "source_ref" in first
    assert "input_schema" in first


def test_list_capability_catalog_includes_runtime_and_agent_tool_items():
    items = list_capability_catalog()
    ids = {item["id"] for item in items}

    assert "runtime.agent_custom" in ids
    assert "shopify.get_order" in ids
    assert "shopify.order_action" in ids
    assert "runtime.shopify_get_order" not in ids
    assert "runtime.shopify_order_action" not in ids
    assert "agent_tool.knowledge_search" in ids
