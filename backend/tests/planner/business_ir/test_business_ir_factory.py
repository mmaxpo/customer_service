from app.tcos.planner.business_ir import (
    BusinessTaskCategory,
    simple_linear_plan,
    task_with_capability,
    validate_business_plan,
)
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)


def test_simple_linear_plan_creates_edges():
    tasks = [
        task_with_capability(
            task_id="a",
            name="A",
            category=BusinessTaskCategory.ACTION,
            capability_id="runtime.response",
        ),
        task_with_capability(
            task_id="b",
            name="B",
            category=BusinessTaskCategory.ACTION,
            capability_id="runtime.response",
        ),
    ]

    plan = simple_linear_plan(
        plan_id="p",
        goal_id="g",
        goal_title="Goal",
        tasks=tasks,
    )

    assert len(plan.edges) == 1
    assert plan.edges[0].source == "a"
    assert plan.edges[0].target == "b"
    assert validate_business_plan(plan) == []


def test_url_summary_example_plan_is_valid():
    plan = build_url_summary_business_plan(
        "Summarize https://example.com"
    )

    assert validate_business_plan(plan) == []

    assert [
        task.id
        for task in plan.tasks
    ] == [
        "fetch_url",
        "summarize_content",
        "send_response",
    ]

    assert [
        task.required_capabilities[0].capability_id
        for task in plan.tasks
    ] == [
        "runtime.web_fetch_extract",
        "runtime.llm_generate",
        "runtime.response",
    ]
