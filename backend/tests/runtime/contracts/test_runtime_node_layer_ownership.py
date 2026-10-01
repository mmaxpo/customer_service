import ast
from pathlib import Path

from app.node_registration import (
    register_application_nodes,
)
from app.runtime.nodes.registry.builtins import (
    register_core_nodes,
)
from app.runtime.nodes.registry.core import (
    NODE_REGISTRY,
)


def test_core_node_registration_is_product_and_provider_free():
    NODE_REGISTRY.clear()

    register_core_nodes()

    ids = set(NODE_REGISTRY)

    assert len(ids) == 22

    assert not any(
        item.startswith("customer_service.")
        for item in ids
    )

    assert not any(
        item.startswith("shopify.")
        for item in ids
    )

    assert "reply.customer_chat" not in ids


def test_application_node_composition_registers_three_layers():
    NODE_REGISTRY.clear()

    register_application_nodes()

    ids = set(NODE_REGISTRY)

    product = {
        item
        for item in ids
        if (
            item.startswith("customer_service.")
            or item == "reply.customer_chat"
        )
    }

    provider = {
        item
        for item in ids
        if item.startswith("shopify.")
    }

    core = ids - product - provider

    assert len(core) == 22

    assert product == {
        "customer_service.extract_order_ref",
        "customer_service.load_conversation",
        "customer_service.project_support_outcome",
        "customer_service.record_support_outcome",
        "reply.customer_chat",
    }

    assert provider == {
        "shopify.get_order",
        "shopify.order_action",
    }


def test_core_runtime_nodes_do_not_import_product_or_provider():
    root = Path(
        "app/runtime/nodes"
    )

    forbidden = (
        "app.domains.customer_service",
        "app.providers.shopify",
    )

    hits = []

    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue

        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
            ),
            filename=str(path),
        )

        for node in ast.walk(tree):
            modules = []

            if isinstance(
                node,
                ast.ImportFrom,
            ):
                modules.append(
                    node.module or ""
                )

            elif isinstance(
                node,
                ast.Import,
            ):
                modules.extend(
                    alias.name
                    for alias in node.names
                )

            for module in modules:
                if module.startswith(
                    forbidden
                ):
                    hits.append(
                        (
                            path.as_posix(),
                            module,
                        )
                    )

    assert hits == []
