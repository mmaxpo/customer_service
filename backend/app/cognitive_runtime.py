from __future__ import annotations

from collections.abc import Callable

from app.node_registration import register_application_nodes
from app.runtime.nodes.registry import list_registered_nodes
from app.runtime.capabilities.registry.defaults import (
    build_default_capability_registry,
)
from app.tcos.cognitive import CognitiveRuntime
from app.tcos.planner.product_planning import (
    build_default_product_planner_registry,
)


def runtime_node_for_capability(
    capability_id: str,
) -> str | None:
    """
    Resolve an owner-defined discovery capability id to its
    registered runtime node type.

    Product and Provider node packages own discovery_id/type_name.
    Core consumers receive only this generic resolver.
    """
    normalized = str(
        capability_id or ""
    ).strip()

    if not normalized:
        return None

    for item in list_registered_nodes():
        node_type = str(
            item.get("node_type") or ""
        ).strip()

        if not node_type:
            continue

        discovery_id = str(
            item.get("discovery_id") or ""
        ).strip()

        fallback_id = (
            f"runtime.{node_type.replace('.', '_')}"
        )

        if normalized in {
            discovery_id,
            fallback_id,
            node_type,
        }:
            return node_type

    return None


def build_application_cognitive_runtime(
    *,
    is_semantic_capability: Callable[[str], bool] | None = None,
) -> CognitiveRuntime:
    """
    Build the Cognitive Runtime installed in this application.

    Core CognitiveRuntime remains product-neutral.

    Product implementations are registered here at the application
    composition boundary, just like application workflow-node
    registration.

    Dependency direction:

        application composition
            -> autonomous Core
            -> installed Products

    Core never imports Product implementations.
    """

    # Application composition owns installation of Core,
    # Product, and Provider runtime nodes.
    register_application_nodes()

    product_planners = (
        build_default_product_planner_registry()
    )

    semantic_capability_predicate = (
        is_semantic_capability
    )

    if semantic_capability_predicate is None:
        semantic_capability_predicate = (
            build_default_capability_registry()
            .has_capability
        )

    # Import Product registration lazily so importing this module does
    # not force Product model initialization unnecessarily.
    from app.domains.customer_service.services.support.planning.customer_support_product_planner_registry import (
        register_customer_support_product_planner,
    )

    register_customer_support_product_planner(
        product_planners
    )

    return CognitiveRuntime(
        product_planners=product_planners,
        is_semantic_capability=(
            semantic_capability_predicate
        ),
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    )


__all__ = [
    "build_application_cognitive_runtime",
]
