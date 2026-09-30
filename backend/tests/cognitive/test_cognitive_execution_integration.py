from app.tcos.cognitive import CognitiveRuntime, CognitiveSessionStatus


def test_cognitive_runtime_prepares_execution_session():
    session = CognitiveRuntime().execute_goal(goal="Summarize https://example.com")

    assert session.status == CognitiveSessionStatus.COMPLETED
    assert session.execution_session is not None
    assert session.execution_session["runtime_workflow"]["nodes"]
    assert session.execution_session["metrics"]["node_count"] > 0


def test_cognitive_runtime_records_execution_prepared_event():
    session = CognitiveRuntime().execute_goal(goal="Summarize https://example.com")

    event_types = [event.type for event in session.events]

    assert event_types == [
        "CognitiveSessionCreated",
        "PlannerCompleted",
        "ExecutionPrepared",
        "CognitiveSessionCompleted",
    ]


def test_failed_cognitive_session_does_not_prepare_execution():
    session = CognitiveRuntime().execute_goal(goal="Build a quarterly revenue forecast")

    assert session.status == CognitiveSessionStatus.FAILED
    assert session.execution_session is None
    assert session.metrics["execution_prepared"] is False
