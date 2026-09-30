from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningInsightPromotionOperations,
)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


@pytest.mark.asyncio
async def test_promotion_routes_are_authenticated_and_scoped(
    monkeypatch,
):
    user_id = uuid4()
    candidate_id = uuid4()
    promotion_id = uuid4()
    captured = {}

    async def fake_promote(
        self,
        **kwargs,
    ):
        captured["promote"] = kwargs
        return None

    async def fake_list_latest(
        self,
        **kwargs,
    ):
        captured["list"] = kwargs
        return []

    async def fake_get_latest(
        self,
        **kwargs,
    ):
        captured["get"] = kwargs
        return None

    async def fake_history(
        self,
        **kwargs,
    ):
        captured["history"] = kwargs
        return []

    async def fake_revoke(
        self,
        **kwargs,
    ):
        captured["revoke"] = kwargs
        return None

    monkeypatch.setattr(
        CapabilityLearningInsightPromotionOperations,
        "promote",
        fake_promote,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightPromotionOperations,
        "list_latest",
        fake_list_latest,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightPromotionOperations,
        "get_latest",
        fake_get_latest,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightPromotionOperations,
        "history",
        fake_history,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightPromotionOperations,
        "revoke",
        fake_revoke,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            promoted = await client.post(
                "/capabilities/"
                "learning-insight-candidates/"
                f"{candidate_id}/promotions",
                json={"reason": "Promote."},
            )

            listed = await client.get(
                "/capabilities/"
                "learning-insight-promotions",
                params={
                    "status": "active",
                    "candidate_id": str(
                        candidate_id
                    ),
                    "limit": 20,
                },
            )

            fetched = await client.get(
                "/capabilities/"
                "learning-insight-promotions/"
                f"{promotion_id}"
            )

            history = await client.get(
                "/capabilities/"
                "learning-insight-promotions/"
                f"{promotion_id}/history"
            )

            revoked = await client.post(
                "/capabilities/"
                "learning-insight-promotions/"
                f"{promotion_id}/revoke",
                json={"reason": "Revoke."},
            )

        assert promoted.status_code == 404
        assert listed.status_code == 200
        assert fetched.status_code == 404
        assert history.status_code == 404
        assert revoked.status_code == 404

        assert captured[
            "promote"
        ]["user_id"] == user_id
        assert captured[
            "promote"
        ]["candidate_id"] == candidate_id
        assert captured[
            "promote"
        ]["created_by_user_id"] == user_id

        assert captured["list"]["user_id"] == (
            user_id
        )
        assert captured[
            "list"
        ]["candidate_id"] == candidate_id
        assert captured[
            "list"
        ]["status"] == "active"

        assert captured["get"]["user_id"] == (
            user_id
        )
        assert captured[
            "get"
        ]["promotion_id"] == promotion_id

        assert captured[
            "history"
        ]["user_id"] == user_id

        assert captured[
            "revoke"
        ]["user_id"] == user_id
        assert captured[
            "revoke"
        ]["created_by_user_id"] == user_id
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_promotion_lifecycle_errors_map_to_422(
    monkeypatch,
):
    user_id = uuid4()

    async def fake_promote(
        self,
        **kwargs,
    ):
        raise ValueError(
            "Candidate already has an active "
            "promotion"
        )

    async def fake_revoke(
        self,
        **kwargs,
    ):
        raise ValueError(
            "Only an active promotion can "
            "be revoked"
        )

    monkeypatch.setattr(
        CapabilityLearningInsightPromotionOperations,
        "promote",
        fake_promote,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightPromotionOperations,
        "revoke",
        fake_revoke,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            promoted = await client.post(
                "/capabilities/"
                "learning-insight-candidates/"
                f"{uuid4()}/promotions",
                json={"reason": "Promote."},
            )

            revoked = await client.post(
                "/capabilities/"
                "learning-insight-promotions/"
                f"{uuid4()}/revoke",
                json={"reason": "Revoke."},
            )

        assert promoted.status_code == 422
        assert revoked.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
