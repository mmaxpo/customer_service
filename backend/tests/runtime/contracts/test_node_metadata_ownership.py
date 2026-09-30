from app.node_registration import register_application_nodes
from app.runtime.nodes.registry import list_registered_nodes
from app.runtime.nodes.registry.core import NODE_REGISTRY
from app.tcos.capabilities.service import build_capability_registry


def _registered_nodes():
    NODE_REGISTRY.clear()
    register_application_nodes()

    return {
        item["node_type"]: item
        for item in list_registered_nodes()
    }


def test_customer_service_nodes_own_semantic_metadata():
    by_type = _registered_nodes()

    expected = {
        "customer_service.extract_order_ref": {
            "title": "Extract Order Reference",
            "category": "data",
            "group": "Data",
            "domain": "customer_service",
        },
        "customer_service.project_support_outcome": {
            "title": "Project Support Outcome",
            "category": "data",
            "group": "Data",
            "domain": "customer_service",
        },
        "customer_service.record_support_outcome": {
            "title": "Record Support Outcome",
            "category": "data",
            "group": "Data",
            "domain": "customer_service",
        },
        "reply.customer_chat": {
            "title": "Customer Chat Reply",
            "category": "output",
            "group": "Output",
            "domain": "customer_service",
        },
    }

    for node_type, metadata in expected.items():
        for key, value in metadata.items():
            assert by_type[node_type][key] == value


def test_shopify_nodes_own_semantic_metadata():
    by_type = _registered_nodes()

    expected = {
        "shopify.get_order": {
            "title": "Shopify Get Order",
            "category": "data",
            "group": "Data",
            "domain": "shopify",
        },
        "shopify.order_action": {
            "title": "Shopify Order Action",
            "category": "platform",
            "group": "Platform",
            "domain": "shopify",
        },
    }

    for node_type, metadata in expected.items():
        for key, value in metadata.items():
            assert by_type[node_type][key] == value


def test_core_ui_metadata_remains_unchanged():
    by_type = _registered_nodes()

    assert by_type["agent.custom"]["title"] == "Custom Agent"
    assert by_type["agent.custom"]["category"] == "agent"
    assert by_type["agent.custom"]["group"] == "AI"
    assert by_type["agent.custom"]["domain"] == "agent"

    assert by_type["response"]["title"] == "Response"
    assert by_type["response"]["category"] == "output"
    assert by_type["response"]["group"] == "Output"
    assert by_type["response"]["domain"] == "communication"


def test_tcos_reads_owner_metadata_mechanically():
    by_id = {
        item.id: item
        for item in build_capability_registry().list()
    }

    assert (
        by_id["customer_service.extract_order_ref"].domain
        == "customer_service"
    )
    assert (
        by_id["customer_service.extract_order_ref"].category
        == "data"
    )
    assert (
        by_id["customer_service.extract_order_ref"].title
        == "Extract Order Reference"
    )

    assert by_id["reply.customer_chat"].domain == "customer_service"
    assert by_id["reply.customer_chat"].category == "output"
    assert by_id["reply.customer_chat"].title == "Customer Chat Reply"

    assert by_id["shopify.get_order"].domain == "shopify"
    assert by_id["shopify.get_order"].category == "data"
    assert by_id["shopify.get_order"].title == "Shopify Get Order"

    assert by_id["shopify.order_action"].domain == "shopify"
    assert by_id["shopify.order_action"].category == "platform"
    assert (
        by_id["shopify.order_action"].title
        == "Shopify Order Action"
    )
