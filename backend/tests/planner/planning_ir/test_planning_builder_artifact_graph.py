from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.planning_builder import PlanningBuilder
from app.tcos.planner.planning_ir import ArtifactKind


def test_url_summary_planning_plan_contains_produced_artifacts():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    artifact_ids = {artifact.id for artifact in planning.artifacts}

    assert "web_extract" in artifact_ids
    assert "summary" in artifact_ids


def test_fetch_url_produces_document_artifact():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    fetch = next(op for op in planning.operations if op.id == "fetch_url")
    artifact = fetch.produces[0]

    assert artifact.id == "web_extract"
    assert artifact.kind == ArtifactKind.DOCUMENT
    assert artifact.producer_task_id == "fetch_url"
    assert fetch.invocation.produces[0].id == "web_extract"


def test_summarize_content_produces_text_artifact():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    summarize = next(op for op in planning.operations if op.id == "summarize_content")
    artifact = summarize.produces[0]

    assert artifact.id == "summary"
    assert artifact.kind == ArtifactKind.TEXT
    assert artifact.producer_task_id == "summarize_content"
    assert summarize.invocation.produces[0].id == "summary"
