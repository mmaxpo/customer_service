from app.tcos.planner.runtime import PlannerRuntime, PlanningStatus


def test_unknown_intent_does_not_create_repair_result_before_candidate():
    session = PlannerRuntime().plan_goal(
        goal="Build a quarterly revenue forecast"
    )

    assert session.status == PlanningStatus.FAILED
    assert session.repair_result is None


def test_planner_session_has_repair_result_field():
    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    assert hasattr(session, "repair_result")
    assert session.repair_result is None
