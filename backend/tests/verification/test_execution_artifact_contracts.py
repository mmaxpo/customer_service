from app.tcos.compiler import compile_business_plan, compile_planning_plan
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.planning_ir import (
    InvocationInput,
    PlanningCapabilityInvocation,
    PlanningOperation,
    PlanningPlan,
)


def test_url_summary_execution_graph_has_valid_artifact_contracts():
    result = compile_business_plan(
        build_url_summary_business_plan(
            "Summarize this URL for me: https://example.com"
        )
    )

    assert result.ok is True

    produced = set()

    for node in result.execution_graph.nodes:
        for item in node.inputs:
            assert item["artifact_id"] in produced

        for item in node.outputs:
            produced.add(item["artifact_id"])


def test_compile_rejects_missing_artifact_producer():
    plan = PlanningPlan(
        id="planning_missing_artifact",
        business_plan_id="business_missing_artifact",
        operations=[
            PlanningOperation(
                id="reply",
                business_task_id="reply",
                objective="Reply",
                operation_type="communicate",
                selected_capability="runtime.response",
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.response",
                    arguments={"answer_from": "missing_summary"},
                    inputs=[InvocationInput(artifact_id="missing_summary")],
                ),
            )
        ],
    )

    result = compile_planning_plan(plan)

    assert result.ok is False
    assert any(d.code == "missing_artifact_producer" for d in result.diagnostics)
