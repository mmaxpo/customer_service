from app.tcos.cognitive import CognitiveRuntime, CognitiveSessionStatus


def test_cognitive_runtime_executes_goal_through_planner():
    session = CognitiveRuntime().execute_goal(goal="Summarize https://example.com")

    assert session.status == CognitiveSessionStatus.COMPLETED
    assert session.planner_session is not None
    assert session.planner_session["status"] == "compiled"


def test_cognitive_runtime_records_events():
    session = CognitiveRuntime().execute_goal(goal="Summarize https://example.com")

    event_types = [event.type for event in session.events]

    assert event_types == [
        "CognitiveSessionCreated",
        "PlannerCompleted",
        "ExecutionPrepared",
        "CognitiveSessionCompleted",
    ]


def test_cognitive_runtime_fails_when_planner_fails():
    session = CognitiveRuntime().execute_goal(goal="Build a quarterly revenue forecast")

    assert session.status == CognitiveSessionStatus.FAILED
    assert session.planner_session["status"] == "failed"
