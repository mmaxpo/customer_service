from app.tcos.planner.business_ir import (
    analyze_business_plan,
)
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)


def test_business_plan_analysis():
    plan = build_url_summary_business_plan(
        "Summarize https://example.com"
    )

    analysis = analyze_business_plan(plan)

    assert analysis.entry_tasks == ["fetch_url"]
    assert analysis.exit_tasks == ["send_response"]
    assert analysis.critical_path == [
        "fetch_url",
        "summarize_content",
        "send_response",
    ]
    assert analysis.capability_ids == [
        "runtime.llm_generate",
        "runtime.response",
        "runtime.web_fetch_extract",
    ]
    assert analysis.metrics["task_count"] == 3
