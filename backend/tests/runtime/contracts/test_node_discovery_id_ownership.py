from app.node_registration import (
    register_application_nodes,
)
from app.runtime.nodes.registry import (
    list_registered_nodes,
)
from app.runtime.nodes.registry.core import (
    NODE_REGISTRY,
)
from app.tcos.capabilities.service import (
    build_capability_registry,
)


def test_non_core_node_owners_define_discovery_ids():
    NODE_REGISTRY.clear()

    register_application_nodes()

    by_type = {
        item["node_type"]: item
        for item in list_registered_nodes()
    }

    expected = {
        "customer_service.extract_order_ref":
            "customer_service.extract_order_ref",

        "customer_service.project_support_outcome":
            "customer_service.project_support_outcome",

        "customer_service.record_support_outcome":
            "customer_service.record_support_outcome",

        "reply.customer_chat":
            "reply.customer_chat",

        "shopify.get_order":
            "shopify.get_order",

        "shopify.order_action":
            "shopify.order_action",
    }

    for node_type, discovery_id in expected.items():
        assert (
            by_type[node_type]["discovery_id"]
            == discovery_id
        )


def test_core_nodes_use_generic_runtime_discovery_namespace():
    NODE_REGISTRY.clear()

    register_application_nodes()

    by_type = {
        item["node_type"]: item
        for item in list_registered_nodes()
    }

    assert (
        by_type["response"]["discovery_id"]
        is None
    )
    assert (
        by_type["wait.event"]["discovery_id"]
        is None
    )
    assert (
        by_type["capability.invoke"]["discovery_id"]
        is None
    )


def test_tcos_catalog_uses_one_identity_per_runtime_node():
    registry = build_capability_registry()

    ids = {
        item.id
        for item in registry.list()
    }

    # Core-owned IDs.
    assert "runtime.response" in ids
    assert "runtime.wait_event" in ids
    assert "runtime.capability_invoke" in ids

    # Product-owned IDs.
    assert "customer_service.extract_order_ref" in ids
    assert "customer_service.project_support_outcome" in ids
    assert "customer_service.record_support_outcome" in ids
    assert "reply.customer_chat" in ids

    # Provider-owned IDs.
    assert "shopify.get_order" in ids
    assert "shopify.order_action" in ids

    # TCOS must not fabricate Core-looking aliases for
    # Product or Provider nodes.
    assert (
        "runtime.customer_service_extract_order_ref"
        not in ids
    )
    assert (
        "runtime.customer_service_project_support_outcome"
        not in ids
    )
    assert (
        "runtime.customer_service_record_support_outcome"
        not in ids
    )
    assert "runtime.reply_customer_chat" not in ids
    assert "runtime.shopify_get_order" not in ids
    assert "runtime.shopify_order_action" not in ids

    # 28 runtime nodes + 4 built-in agent tools.
    assert len(ids) == 32
