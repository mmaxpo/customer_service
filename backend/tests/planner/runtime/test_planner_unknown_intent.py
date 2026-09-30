from app.tcos.planner.runtime import PlannerRuntime, PlanningStatus


def test_planner_runtime_fails_safely_for_unknown_intent():
    session = PlannerRuntime().plan_goal(
        goal="Build a quarterly revenue forecast"
    )

    assert session.status == PlanningStatus.FAILED
    assert session.compilation is None
    assert session.business_plan is None
    assert session.metrics["compiled"] is False
    assert (
        "No generic Business Plan builder registered for unknown"
        in session.metrics["failure_reason"]
    )
    assert "PlanningFailed" in [event.type for event in session.events]
