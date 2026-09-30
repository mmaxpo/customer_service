from app.runtime.nodes.registry import (
    get_node,
    list_registered_nodes,
    register_node,
)
from app.node_registration import (
    register_application_nodes,
)


class ExampleNode:
    pass


def test_register_node_owns_discovery_metadata():
    register_node(
        "test.discovery_metadata",
        ExampleNode,
        title="Test Discovery Node",
        icon="node",
        category="data",
        group="Data",
        domain="testing",
        risk_level="sensitive",
        requires_approval=True,
    )

    registration = get_node(
        "test.discovery_metadata"
    )

    assert registration.title == "Test Discovery Node"
    assert registration.icon == "node"
    assert registration.category == "data"
    assert registration.group == "Data"
    assert registration.domain == "testing"
    assert registration.risk_level == "sensitive"
    assert registration.requires_approval is True

    item = next(
        item
        for item in list_registered_nodes()
        if item["node_type"]
        == "test.discovery_metadata"
    )

    assert item["title"] == "Test Discovery Node"
    assert item["icon"] == "node"
    assert item["category"] == "data"
    assert item["group"] == "Data"
    assert item["domain"] == "testing"
    assert item["risk_level"] == "sensitive"
    assert item["requires_approval"] is True


def test_builtin_safety_metadata_is_registered():
    register_application_nodes()

    by_type = {
        item["node_type"]: item
        for item in list_registered_nodes()
    }

    assert (
        by_type["human.approval"]["risk_level"]
        == "sensitive"
    )
    assert (
        by_type["human.approval"]["requires_approval"]
        is True
    )

    assert (
        by_type["knowledge.ingest"]["risk_level"]
        == "sensitive"
    )

    assert (
        by_type["platform.job.enqueue"]["risk_level"]
        == "sensitive"
    )

    assert (
        by_type["shopify.order_action"]["risk_level"]
        == "sensitive"
    )


def test_generic_nodes_keep_existing_domain_mapping():
    register_application_nodes()

    by_type = {
        item["node_type"]: item
        for item in list_registered_nodes()
    }

    assert (
        by_type["agent.custom"]["domain"]
        == "agent"
    )
    assert (
        by_type["wait.event"]["domain"]
        == "control"
    )
    assert (
        by_type["response"]["domain"]
        == "communication"
    )
    assert (
        by_type["web.search"]["domain"]
        == "web"
    )
