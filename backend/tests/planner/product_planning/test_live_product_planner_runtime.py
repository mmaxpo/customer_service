from __future__ import annotations

from app.cognitive_runtime import (
    runtime_node_for_capability,
)
from app.domains.customer_service.services.support.planning.customer_support_product_planner_registry import (
    register_customer_support_product_planner,
)
from app.runtime.capabilities.registry.defaults import (
    build_default_capability_registry,
)
from app.tcos.planner.product_planning import (
    build_default_product_planner_registry,
)
from app.tcos.planner.runtime import (
    PlannerRuntime,
    PlanningStatus,
)


def _runtime() -> PlannerRuntime:
    products = build_default_product_planner_registry()

    register_customer_support_product_planner(products)

    capabilities = build_default_capability_registry()

    return PlannerRuntime(
        product_planners=products,
        is_semantic_capability=(capabilities.has_capability),
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    )


def test_missing_order_becomes_noncompiled_clarification():
    session = _runtime().plan_goal(
        goal=("My order hasn't arrived. Check it for me.")
    )

    assert session.status == (PlanningStatus.CLARIFICATION_REQUIRED)

    assert session.compilation is None
    assert session.business_plan is None
    assert session.selected_candidate is None

    assert session.clarification is not None
    assert session.clarification["reason_code"] == ("missing_order_ref")
    assert session.clarification["missing_fields"] == ["order_ref"]

    assert session.metrics["clarification_required"] is True
    assert session.metrics["compiled"] is False

    event_types = [event.type for event in session.events]

    assert "PlanningClarificationRequired" in (event_types)

    assert "BusinessPlanCreated" not in event_types
    assert "CompilationSucceeded" not in event_types


def test_known_order_live_plan_compiles_semantic_capability():
    session = _runtime().plan_goal(
        goal=("Reply to customer: Where is order #1001?")
    )

    assert session.status == PlanningStatus.COMPILED
    assert session.compilation is not None
    assert session.compilation.ok is True
    assert session.compilation.execution_graph is not None

    lookup = next(
        node
        for node in session.compilation.execution_graph.nodes
        if node.id == "lookup_order"
    )

    assert lookup.node_type == "capability.invoke"

    assert lookup.config["capability_id"] == ("ecommerce.orders.get")
    assert lookup.config["input_from"] == "vars"
    assert lookup.config["input_key"] == "order_ref"
    assert lookup.config["save_as"] == "commerce_order"

    serialized = session.model_dump_json().lower()

    assert "shopify.get_order" not in serialized
