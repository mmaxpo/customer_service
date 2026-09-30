from app.tcos.compiler import compile_planning_plan
from app.tcos.planner.planning_ir import (
    PlanningCapabilityInvocation,
    PlanningOperation,
    PlanningPlan,
)


def test_compiler_does_not_read_operation_metadata_config():
    plan = PlanningPlan(
        id="planning_no_metadata_config",
        business_plan_id="business_no_metadata_config",
        operations=[
            PlanningOperation(
                id="reply",
                business_task_id="reply",
                objective="Reply",
                operation_type="communicate",
                selected_capability="runtime.response",
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.response",
                    arguments={"answer_from": "last"},
                ),
                metadata={"config": {"answer_from": "metadata_should_not_win"}},
            )
        ],
    )

    result = compile_planning_plan(plan)

    assert result.ok is True

    node = next(node for node in result.execution_graph.nodes if node.id == "reply")
    assert node.config["answer_from"] == "last"
