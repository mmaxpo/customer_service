from fastapi.testclient import TestClient

from app.main import app


def test_tcos_route_exists():
    routes = {route.path for route in app.routes}

    assert "/tcos/execute-goal" in routes


def test_cognitive_runtime_still_available():
    from app.tcos.cognitive import CognitiveRuntime

    session = CognitiveRuntime().execute_goal(goal="Summarize https://example.com")

    assert session.status.value == "completed"
