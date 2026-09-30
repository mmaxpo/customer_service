from fastapi.routing import APIRoute

from app.main import app


def test_customer_service_inbox_routes_are_registered_once():
    inbox_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and "Customer Service - Inbox" in (route.tags or [])
    ]

    registered = {
        (route.path, tuple(sorted(route.methods or []))) for route in inbox_routes
    }

    assert registered == {
        ("/customer-service/inbox/", ("GET",)),
        ("/customer-service/inbox/email/ingest", ("POST",)),
        (
            "/customer-service/inbox/email/webhooks/resend/{workspace_id}",
            ("POST",),
        ),
    }


def test_customer_service_routes_have_no_duplicate_path_method_pairs():
    route_keys = [
        (route.path, method)
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/customer-service")
        for method in sorted(route.methods or [])
    ]

    duplicates = {key for key in route_keys if route_keys.count(key) > 1}

    assert duplicates == set()


def test_customer_service_key_routes_are_registered():
    route_keys = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/customer-service")
    }

    expected = {
        ("/customer-service/dashboard", ("GET",)),
        ("/customer-service/conversations/{conversation_id}/messages", ("GET",)),
        ("/customer-service/conversations/{conversation_id}/messages", ("POST",)),
        ("/customer-service/customers/{customer_id}/360", ("GET",)),
        ("/customer-service/customers/{customer_id}/activity", ("GET",)),
        ("/customer-service/customers/{customer_id}/risk", ("GET",)),
        ("/customer-service/customers/risk-leaderboard", ("GET",)),
        ("/customer-service/conversations/{conversation_id}/context", ("GET",)),
        ("/customer-service/conversations/{conversation_id}/timeline", ("GET",)),
        (
            "/customer-service/conversations/{conversation_id}/workspace-recommendations",
            ("GET",),
        ),
        ("/customer-service/omnichannel/inbound", ("POST",)),
        ("/customer-service/omnichannel/outbound/enqueue", ("POST",)),
    }

    missing = expected - route_keys

    assert missing == set()
