from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.tcos.capabilities.planner_advisory_composition import (
    CapabilityAdvisoryMatchResponse,
    CapabilityPlannerAdvisoryComposer,
)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


@pytest.mark.asyncio
async def test_advisory_aware_match_is_authenticated_and_scoped(
    monkeypatch,
):
    user_id = uuid4()
    captured = {}

    async def fake_compose(
        self,
        *,
        user_id,
        request,
    ):
        captured["user_id"] = user_id
        captured["request"] = request

        return CapabilityAdvisoryMatchResponse(
            query=request.query,
            matches=[],
        )

    monkeypatch.setattr(
        CapabilityPlannerAdvisoryComposer,
        "compose",
        fake_compose,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/capabilities/"
                "match/advisory-aware",
                json={
                    "query": "knowledge",
                    "tenant_id": "tenant-a",
                    "provider_id": "builtin",
                    "provider_ref": None,
                    "action": "search",
                    "limit": 5,
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "knowledge"
        assert data["matches"] == []
        assert (
            data[
                "ranking_affected_by_advisories"
            ]
            is False
        )

        assert captured["user_id"] == user_id
        assert (
            captured["request"].tenant_id
            == "tenant-a"
        )
        assert (
            captured["request"].provider_id
            == "builtin"
        )
        assert (
            captured["request"].action
            == "search"
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_existing_match_route_remains_unchanged():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/capabilities/match",
            json={
                "query": "knowledge",
                "limit": 5,
            },
        )

    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "knowledge"
    assert data["matches"]
    assert (
        "ranking_affected_by_advisories"
        not in data
    )
