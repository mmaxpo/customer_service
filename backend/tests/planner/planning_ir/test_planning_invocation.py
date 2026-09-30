from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.planning_builder import PlanningBuilder


def test_planning_operation_contains_invocation():
    business = build_url_summary_business_plan("Summarize https://example.com")

    planning = PlanningBuilder().build(business)

    fetch = next(op for op in planning.operations if op.id == "fetch_url")

    assert fetch.invocation is not None
    assert fetch.invocation.capability_id == "runtime.web_fetch_extract"
    assert fetch.invocation.arguments["url"] == "https://example.com"


def test_llm_invocation_contains_prompt():
    business = build_url_summary_business_plan("Summarize https://example.com")

    planning = PlanningBuilder().build(business)

    summarize = next(op for op in planning.operations if op.id == "summarize_content")

    assert summarize.invocation is not None
    assert "{{ web_extract.text }}" in summarize.invocation.arguments["prompt"]
