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


def _compile(operations):
    business_plan = BusinessPlanBuilder().from_operations(
        plan_id="capability_binding_plan",
        goal_title="capability.binding.test",
        operations=operations,
    )

    planning_plan = PlanningBuilder().build(business_plan)

    registry = build_default_capability_registry()

    return compile_planning_plan(
        planning_plan,
        is_semantic_capability=registry.has_capability,
        runtime_node_for_capability=(
            _runtime_node_for_capability
        ),
    )


def test_single_input_and_output_bind_to_runtime_vars():
    result = _compile(
        [
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
                purpose="Return order.",
                inputs=["commerce_order"],
                depends_on=["lookup"],
            ),
        ]
    )

    assert result.ok is True
    assert result.execution_graph is not None

    lookup = next(node for node in result.execution_graph.nodes if node.id == "lookup")

    assert lookup.config["capability_id"] == ("ecommerce.orders.get")
    assert lookup.config["input_from"] == "vars"
    assert lookup.config["input_key"] == "order_ref"
    assert "input_keys" not in lookup.config
    assert lookup.config["save_as"] == "commerce_order"


def test_multiple_inputs_bind_as_selected_runtime_vars():
    result = _compile(
        [
            PlanningOperation(
                id="seed_order",
                capability_id=("customer_service.extract_order_ref"),
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose="Produce order reference.",
                outputs=["order_ref"],
            ),
            PlanningOperation(
                id="seed_action",
                capability_id="runtime.agent_custom",
                operation_type=OperationType.ANALYZE,
                purpose="Produce action.",
                outputs=["action"],
                depends_on=["seed_order"],
            ),
            PlanningOperation(
                id="perform_action",
                capability_id="ecommerce.orders.action",
                operation_type=OperationType.EXECUTE,
                purpose="Perform semantic order action.",
                inputs=["order_ref", "action"],
                outputs=["action_result"],
                depends_on=[
                    "seed_order",
                    "seed_action",
                ],
            ),
            PlanningOperation(
                id="response",
                capability_id="runtime.response",
                operation_type=OperationType.COMMUNICATE,
                purpose="Return action result.",
                inputs=["action_result"],
                depends_on=["perform_action"],
            ),
        ]
    )

    assert result.ok is True
    assert result.execution_graph is not None

    action = next(
        node for node in result.execution_graph.nodes if node.id == "perform_action"
    )

    assert action.config["input_from"] == "vars"
    assert action.config["input_keys"] == [
        "order_ref",
        "action",
    ]
    assert "input_key" not in action.config
    assert action.config["save_as"] == "action_result"


def test_explicit_legacy_runtime_binding_wins():
    result = _compile(
        [
            PlanningOperation(
                id="extract",
                capability_id=("customer_service.extract_order_ref"),
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose="Extract order reference.",
                outputs=["order_ref"],
            ),
            PlanningOperation(
                id="legacy_lookup",
                capability_id="shopify.get_order",
                operation_type=(OperationType.ACQUIRE_INFORMATION),
                purpose="Legacy lookup.",
                inputs=["order_ref"],
                outputs=["commerce_order"],
                depends_on=["extract"],
            ),
            PlanningOperation(
                id="response",
                capability_id="runtime.response",
                operation_type=OperationType.COMMUNICATE,
                purpose="Return result.",
                inputs=["commerce_order"],
                depends_on=["legacy_lookup"],
            ),
        ]
    )

    assert result.ok is True
    assert result.execution_graph is not None

    lookup = next(
        node for node in result.execution_graph.nodes if node.id == "legacy_lookup"
    )

    # Direct provider runtime nodes are resolved by composition.
    # Core compiler must not invent provider-specific config.
    assert lookup.node_type == "shopify.get_order"

    # Generic compiler metadata is allowed.
    assert lookup.config["name"] == "Legacy lookup."

    # Provider-specific compiler knowledge is not allowed.
    assert "capability_id" not in lookup.config
    assert "input_from" not in lookup.config
    assert "input_key" not in lookup.config
    assert "input_keys" not in lookup.config
    assert "save_as" not in lookup.config

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
