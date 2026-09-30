from app.tcos.compiler import compile_business_plan
from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.planning_builder import PlanningBuilder


def test_url_summary_response_consumes_summary_artifact():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    response = next(op for op in planning.operations if op.id == "send_response")

    assert [ref.artifact_id for ref in response.consumes] == ["summary"]
    assert [ref.artifact_id for ref in response.invocation.consumes] == ["summary"]


def test_url_summary_response_invocation_uses_summary_answer_from():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    response = next(op for op in planning.operations if op.id == "send_response")

    assert response.invocation.arguments["answer_from"] == "summary"


def test_url_summary_compiler_emits_response_answer_from_summary():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    result = compile_business_plan(business)

    assert result.ok is True

    workflow = execution_graph_to_runtime_workflow(result.execution_graph)
    response = next(node for node in workflow["nodes"] if node["id"] == "send_response")

    assert response["data"]["answer_from"] == "vars"
    assert response["data"]["answer_key"] == "summary"
