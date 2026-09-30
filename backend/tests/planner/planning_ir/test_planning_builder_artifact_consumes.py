from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.planning_builder import PlanningBuilder
from app.tcos.planner.planning_ir import validate_planning_plan


def test_url_summary_summarize_consumes_web_extract():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    summarize = next(op for op in planning.operations if op.id == "summarize_content")

    assert [ref.artifact_id for ref in summarize.consumes] == ["web_extract"]
    assert [ref.artifact_id for ref in summarize.invocation.consumes] == ["web_extract"]


def test_url_summary_artifact_graph_validates_with_consumes():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    assert validate_planning_plan(planning) == []


def test_fetch_url_has_no_consumes_but_produces_web_extract():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    fetch = next(op for op in planning.operations if op.id == "fetch_url")

    assert fetch.consumes == []
    assert fetch.produces[0].id == "web_extract"
