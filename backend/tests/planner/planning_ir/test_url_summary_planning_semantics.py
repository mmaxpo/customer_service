from app.tcos.compiler import compile_business_plan
from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.planning_builder import PlanningBuilder


def test_url_summary_planning_promotes_fetch_url_config():
    business_plan = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning_plan = PlanningBuilder().build(business_plan)

    fetch = next(op for op in planning_plan.operations if op.id == "fetch_url")

    assert fetch.metadata["config"]["url"] == "https://example.com"
    assert fetch.metadata["config"]["artifact_as"] == "web_extract"


def test_url_summary_planning_promotes_llm_prompt_config():
    business_plan = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning_plan = PlanningBuilder().build(business_plan)

    summarize = next(
        op for op in planning_plan.operations if op.id == "summarize_content"
    )

    assert "{{ web_extract.text }}" in summarize.metadata["config"]["prompt"]
    assert summarize.metadata["config"]["save_as"] == "summary"
    assert "summarize" in summarize.metadata["config"]["system"].lower()


def test_url_summary_compiler_emits_runtime_prompt_config():
    business_plan = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    result = compile_business_plan(business_plan)

    assert result.ok is True

    workflow = execution_graph_to_runtime_workflow(result.execution_graph)

    fetch = next(node for node in workflow["nodes"] if node["id"] == "fetch_url")
    summarize = next(
        node for node in workflow["nodes"] if node["id"] == "summarize_content"
    )

    assert fetch["data"]["url"] == "https://example.com"
    assert fetch["data"]["artifact_as"] == "web_extract"
    assert "{{ web_extract.text }}" in summarize["data"]["prompt"]
    assert summarize["data"]["save_as"] == "summary"
