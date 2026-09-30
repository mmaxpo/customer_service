from __future__ import annotations

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


def _build_plan():
    return BusinessPlanBuilder().from_operations(
        plan_id="semantic_artifact_plan",
        goal_title="semantic.artifact.test",
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
                id="answer",
                capability_id="runtime.agent_custom",
                operation_type=OperationType.ANALYZE,
                purpose="Prepare answer.",
                inputs=["commerce_order"],
                outputs=["customer_reply"],
                depends_on=["lookup"],
            ),
        ],
    )


def test_business_ir_preserves_operation_artifact_contract():
    business_plan = _build_plan()

    extract = business_plan.tasks[0]
    lookup = business_plan.tasks[1]
    answer = business_plan.tasks[2]

    assert extract.metadata["operation"]["outputs"] == ["order_ref"]

    assert lookup.metadata["operation"]["inputs"] == ["order_ref"]
    assert lookup.metadata["operation"]["outputs"] == ["commerce_order"]

    assert answer.metadata["operation"]["inputs"] == ["commerce_order"]
    assert answer.metadata["operation"]["outputs"] == ["customer_reply"]


def test_planning_ir_restores_semantic_inputs_and_outputs():
    planning_plan = PlanningBuilder().build(_build_plan())

    extract = planning_plan.operations[0]
    lookup = planning_plan.operations[1]
    answer = planning_plan.operations[2]

    assert extract.invocation is not None
    assert lookup.invocation is not None
    assert answer.invocation is not None

    assert [item.artifact_id for item in extract.invocation.outputs] == ["order_ref"]

    assert [item.artifact_id for item in lookup.invocation.inputs] == ["order_ref"]

    assert [item.artifact_id for item in lookup.invocation.outputs] == [
        "commerce_order"
    ]

    assert [item.artifact_id for item in answer.invocation.inputs] == ["commerce_order"]

    assert [item.artifact_id for item in answer.invocation.outputs] == [
        "customer_reply"
    ]


def test_planning_operation_compatibility_fields_match_invocation():
    planning_plan = PlanningBuilder().build(_build_plan())

    lookup = planning_plan.operations[1]

    assert [item.artifact_id for item in lookup.consumes] == ["order_ref"]

    assert [item.id for item in lookup.produces] == ["commerce_order"]


def test_existing_config_artifacts_are_not_duplicated():
    plan = BusinessPlanBuilder().from_operations(
        plan_id="mixed_artifact_plan",
        goal_title="mixed.artifact.test",
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
                metadata={
                    "config": {
                        "answer_from": "order_ref",
                        "save_as": "commerce_order",
                    }
                },
            ),
        ],
    )

    planning_plan = PlanningBuilder().build(plan)
    lookup = planning_plan.operations[1]

    assert lookup.invocation is not None

    assert [item.artifact_id for item in lookup.invocation.inputs] == ["order_ref"]

    assert [item.artifact_id for item in lookup.invocation.outputs] == [
        "commerce_order"
    ]

    assert [item.artifact_id for item in lookup.consumes] == ["order_ref"]

    assert [item.id for item in lookup.produces] == ["commerce_order"]
