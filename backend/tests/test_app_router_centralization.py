from fastapi.routing import APIRoute

from app.main import app
from app.api.router import api_router


def test_app_includes_central_api_router_routes():
    app_route_keys = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if isinstance(route, APIRoute)
    }

    central_route_keys = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in api_router.routes
        if isinstance(route, APIRoute)
    }

    assert central_route_keys
    assert central_route_keys.issubset(app_route_keys)


def test_app_routes_have_no_duplicate_path_method_pairs():
    route_keys = [
        (route.path, method)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in sorted(route.methods or [])
    ]

    duplicates = {key for key in route_keys if route_keys.count(key) > 1}

    assert duplicates == set()
