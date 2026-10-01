from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class _AllowSignups:
    async def increment(self, *args, **kwargs) -> int:
        return 0


@pytest.fixture(autouse=True)
def _no_signup_rate_limit(monkeypatch):
    # These tests sign up from one address; the limiter is covered elsewhere.
    from app.api import auth as auth_api

    monkeypatch.setattr(auth_api, "_signup_rate_store", _AllowSignups())


async def _authenticated_client() -> AsyncClient:
    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

    email = f"jobs-routing-{uuid4()}@example.com"
    password = f"RoutingTest-{uuid4()}"

    signup = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            "terms_accepted": True,
            "terms_version": "v1",
            "privacy_accepted": True,
            "privacy_version": "v1",
        },
    )
    assert signup.status_code == 201

    login = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login.status_code == 200

    return client


@pytest.mark.asyncio
async def test_jobs_metrics_static_route_is_not_shadowed_by_job_id():
    client = await _authenticated_client()

    try:
        response = await client.get("/jobs/metrics")

        assert response.status_code == 200
        assert isinstance(response.json(), dict)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_jobs_dead_letters_static_route_is_not_shadowed_by_job_id():
    client = await _authenticated_client()

    try:
        response = await client.get("/jobs/dead-letters")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        await client.aclose()
