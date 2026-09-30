from app.tcos.planner.runtime import PlannerRuntime


def test_planner_session_stores_planning_context():
    runtime = PlannerRuntime()

    session = runtime.plan_goal(goal="Where is my order?")

    assert session.context["user_message"] == "Where is my order?"
    assert (
        session.events[0].payload["planning_context"]["user_message"]
        == "Where is my order?"
    )
