from app.tcos.cognitive import (
    CognitiveRuntime,
    compiled_runtime_workflow_from_session,
)


def test_compiled_runtime_workflow_from_cognitive_session():
    session = CognitiveRuntime().execute_goal(goal="Summarize https://example.com")

    workflow = compiled_runtime_workflow_from_session(session)

    assert workflow is not None
    assert workflow["nodes"]
    assert workflow["edges"]
    assert any(node["data"]["nodeType"] == "response" for node in workflow["nodes"])


def test_no_compiled_runtime_workflow_for_failed_session():
    session = CognitiveRuntime().execute_goal(goal="Build a quarterly revenue forecast")

    assert compiled_runtime_workflow_from_session(session) is None
