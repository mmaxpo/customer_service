from __future__ import annotations

from app.runtime.capabilities.registry.defaults import (
    build_default_capability_registry,
)
from app.tcos.compiler.compiler import (
    compile_planning_plan,
)
from app.tcos.planner.operations import (
    OperationType,
    PlanningOperation,
)
from app.tcos.planner.planning_builder import (
    PlanningBuilder,
)
from app.tcos.planner.runtime.business_plan_builder import (
    BusinessPlanBuilder,
)


def _runtime_node_for_capability(
    capability_id: str,
) -> str | None:
    return {
        "customer_service.extract_order_ref": (
            "customer_service.extract_order_ref"
        ),
        "shopify.get_order": "shopify.get_order",
    }.get(capability_id)


def _semantic_planning_plan():
    business_plan = BusinessPlanBuilder().from_operations(
        plan_id="semantic_compile_plan",
        goal_title="semantic.compile.test",
        operations=[
            PlanningOperation(
                id="extract",
                capability_id=("customer_service.extract_order_ref"),
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose="Extract order reference.",
                outputs=["order_ref"],
            ),
            PlanningOperation(
                id="lookup",
                capability_id="ecommerce.orders.get",
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose="Retrieve order.",
                inputs=["order_ref"],
                outputs=["commerce_order"],
                depends_on=["extract"],
            ),
            PlanningOperation(
                id="response",
                capability_id="runtime.response",
                operation_type=OperationType.COMMUNICATE,
                purpose="Return order result.",
                inputs=["commerce_order"],
                depends_on=["lookup"],
            ),
        ],
    )

    return PlanningBuilder().build(business_plan)


def test_semantic_capability_requires_explicit_compiler_knowledge():
    result = compile_planning_plan(_semantic_planning_plan())

    assert result.ok is False

    assert any(
        diagnostic.code == "capability_not_compilable"
        for diagnostic in result.diagnostics
    )


def test_registered_semantic_capability_compiles_to_generic_invoke():
    registry = build_default_capability_registry()

    result = compile_planning_plan(
        _semantic_planning_plan(),
        is_semantic_capability=registry.has_capability,
        runtime_node_for_capability=(
            _runtime_node_for_capability
        ),
    )

    assert result.ok is True
    assert result.execution_graph is not None

    lookup = next(node for node in result.execution_graph.nodes if node.id == "lookup")

    assert lookup.node_type == "capability.invoke"

    assert lookup.config["input_from"] == "vars"
    assert lookup.config["input_key"] == "order_ref"
    assert "input_keys" not in lookup.config
    assert lookup.config["save_as"] == "commerce_order"

    assert lookup.config["capability_id"] == ("ecommerce.orders.get")

    assert lookup.inputs == [
        {
            "artifact_id": "order_ref",
            "required": True,
        }
    ]

    assert lookup.outputs == [
        {
            "artifact_id": "commerce_order",
            "kind": "text",
        }
    ]


def test_compiler_does_not_infer_unregistered_semantic_ids():
    result = compile_planning_plan(
        _semantic_planning_plan(),
        is_semantic_capability=lambda _: False,
    )

    assert result.ok is False

    assert any(
        diagnostic.code == "capability_not_compilable"
        for diagnostic in result.diagnostics
    )


def test_compile_business_plan_threads_semantic_predicate():
    from app.tcos.compiler.compiler import (
        compile_business_plan,
    )

    registry = build_default_capability_registry()

    # Build the BusinessPlan directly for the wrapper contract.
    business_plan = BusinessPlanBuilder().from_operations(
        plan_id="semantic_business_compile_plan",
        goal_title="semantic.business.compile.test",
        operations=[
            PlanningOperation(
                id="extract",
                capability_id=("customer_service.extract_order_ref"),
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose="Extract order reference.",
                outputs=["order_ref"],
            ),
            PlanningOperation(
                id="lookup",
                capability_id="ecommerce.orders.get",
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose="Retrieve order.",
                inputs=["order_ref"],
                outputs=["commerce_order"],
                depends_on=["extract"],
            ),
            PlanningOperation(
                id="response",
                capability_id="runtime.response",
                operation_type=OperationType.COMMUNICATE,
                purpose="Return order result.",
                inputs=["commerce_order"],
                depends_on=["lookup"],
            ),
        ],
    )

    result = compile_business_plan(
        business_plan,
        is_semantic_capability=(registry.has_capability),
        runtime_node_for_capability=(
            _runtime_node_for_capability
        ),
    )

    assert result.ok is True
    assert result.execution_graph is not None

    lookup = next(node for node in result.execution_graph.nodes if node.id == "lookup")

    assert lookup.node_type == "capability.invoke"
    assert lookup.config["capability_id"] == ("ecommerce.orders.get")
