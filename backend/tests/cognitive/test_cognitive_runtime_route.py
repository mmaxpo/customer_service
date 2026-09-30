from app.main import app


def test_tcos_runtime_route_exists():
    routes = {route.path for route in app.routes}

    assert "/tcos/execute-goal-runtime" in routes
