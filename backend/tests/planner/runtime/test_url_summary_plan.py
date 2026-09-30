from app.tcos.compiler import compile_business_plan
from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.runtime import PlannerRuntime, PlanningStatus


def test_url_summary_business_plan_compiles_to_runtime_nodes():
    plan = build_url_summary_business_plan()

    result = compile_business_plan(plan)

    assert result.ok is True
    workflow = execution_graph_to_runtime_workflow(result.execution_graph)
    node_types = [node["data"]["nodeType"] for node in workflow["nodes"]]

    assert "web.fetch_extract" in node_types
    assert "llm.generate" in node_types
    assert "response" in node_types


def test_planner_runtime_selects_url_summary_plan():
    session = PlannerRuntime().plan_goal(
        goal="Summarize this URL for me: https://example.com"
    )

    assert session.status == PlanningStatus.COMPILED
    assert (
        session.selected_candidate["metrics"]["selected_capability"]
        == "generic.url_summary"
    )
    assert session.business_plan.id == "url_summary_plan"
