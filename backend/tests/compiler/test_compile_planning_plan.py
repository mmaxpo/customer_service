from app.tcos.compiler import compile_business_plan, compile_planning_plan
from app.tcos.planner.business_ir.generic_examples import build_url_summary_business_plan
from app.tcos.planner.planning_builder import PlanningBuilder


def test_compile_planning_plan_matches_business_wrapper():
    business_plan = build_url_summary_business_plan("Summarize https://example.com")
    planning_plan = PlanningBuilder().build(business_plan)

    from_planning = compile_planning_plan(planning_plan)
    from_business = compile_business_plan(business_plan)

    assert from_planning.ok is True
    assert from_business.ok is True
    assert from_planning.execution_graph.id == from_business.execution_graph.id
    assert [node.node_type for node in from_planning.execution_graph.nodes] == [
        node.node_type for node in from_business.execution_graph.nodes
    ]


def test_compile_planning_plan_uses_planning_operation_capability():
    business_plan = build_url_summary_business_plan("Summarize https://example.com")
    planning_plan = PlanningBuilder().build(business_plan)

    result = compile_planning_plan(planning_plan)

    node = next(
        node
        for node in result.execution_graph.nodes
        if node.id == "fetch_url"
    )

    assert node.node_type == "web.fetch_extract"
    assert (
        node.metadata["capability_id"]
        == "runtime.web_fetch_extract"
    )
