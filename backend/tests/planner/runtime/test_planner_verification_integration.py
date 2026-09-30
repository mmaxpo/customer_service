from app.tcos.planner.runtime import PlannerRuntime, PlanningStatus


def test_planner_runtime_stores_verification_result():
    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    assert session.status == PlanningStatus.COMPILED
    assert session.verification_result is not None
    assert session.verification_result["passed"] is True
    assert session.verification_result["confidence"]["overall"] == 1.0

    event_types = [event.type for event in session.events]
    assert "VerificationCompleted" in event_types


def test_verification_happens_before_business_plan_created_event():
    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    event_types = [event.type for event in session.events]

    assert event_types.index("VerificationCompleted") < event_types.index(
        "BusinessPlanCreated"
    )
