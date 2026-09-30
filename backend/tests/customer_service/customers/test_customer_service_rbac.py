from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeViewer:
    id = uuid4()
    email = "viewer-rbac@example.com"
    full_name = "Viewer"
    is_active = True
    is_superuser = False
    hashed_password = "x"
    customer_service_role = "viewer"


class FakeOwner:
    id = uuid4()
    email = "owner-rbac@example.com"
    full_name = "Owner"
    is_active = True
    is_superuser = False
    hashed_password = "x"
    customer_service_role = "owner"


class FakeUnknown:
    id = uuid4()
    is_superuser = False


@pytest.mark.asyncio
async def test_viewer_cannot_create_agent():
    app.dependency_overrides[get_current_user] = lambda: FakeViewer()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/agents",
                json={
                    "agent_user_id": str(uuid4()),
                    "display_name": "Blocked Agent",
                    "email": "blocked-agent@example.com",
                    "skills": [],
                    "max_open_tickets": 5,
                },
            )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "customer_service_permission_denied"
        assert response.json()["detail"]["permission"] == "cs.agents.manage"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_owner_can_access_sla_policies():
    app.dependency_overrides[get_current_user] = lambda: FakeOwner()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/customer-service/sla/policies")

        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_unknown_role_has_no_customer_service_permissions():
    from app.domains.customer_service.security.rbac import (
        get_customer_service_role,
        has_customer_service_permission,
    )

    user = FakeUnknown()
    assert get_customer_service_role(user) == "unknown"
    assert not has_customer_service_permission(user, "cs.sla.read")
    assert not has_customer_service_permission(user, "cs.agents.manage")
