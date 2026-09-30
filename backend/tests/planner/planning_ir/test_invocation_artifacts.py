from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.planning_builder import PlanningBuilder
from app.tcos.planner.planning_ir import (
    ArtifactKind,
    PlanningArtifact,
    PlanningCapabilityInvocation,
)


def test_invocation_model_supports_consumes_and_produces():
    invocation = PlanningCapabilityInvocation(
        capability_id="runtime.llm_generate",
        produces=[
            PlanningArtifact(
                id="summary",
                kind=ArtifactKind.TEXT,
                producer_task_id="summarize_content",
            )
        ],
        arguments={"save_as": "summary"},
        expected_artifact="summary",
    )

    assert invocation.produces[0].id == "summary"
    assert invocation.expected_artifact == "summary"


def test_url_summary_fetch_invocation_expected_artifact_from_artifact_as():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    fetch = next(op for op in planning.operations if op.id == "fetch_url")

    assert fetch.invocation.expected_artifact == "web_extract"


def test_url_summary_llm_invocation_expected_artifact_from_save_as():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    planning = PlanningBuilder().build(business)

    summarize = next(op for op in planning.operations if op.id == "summarize_content")

    assert summarize.invocation.expected_artifact == "summary"
