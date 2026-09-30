from app.tcos.planner.runtime import PlannerRuntime


def test_planner_runtime_creates_learning_episode():
    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    assert session.learning_episode is not None
    assert session.learning_episode["planner_session_id"] == session.session_id
    assert session.learning_episode["verification_result"]["passed"] is True


def test_learning_completed_event_recorded():
    session = PlannerRuntime().plan_goal(goal="Summarize https://example.com")

    event_types = [e.type for e in session.events]

    assert event_types[-1] == "LearningCompleted"
