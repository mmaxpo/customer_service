from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningCandidateGenerationResult,
    CapabilityLearningInsightCandidateOperations,
)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


@pytest.mark.asyncio
async def test_candidate_routes_are_authenticated_and_scoped(
    monkeypatch,
):
    user_id = uuid4()
    candidate_id = uuid4()
    captured = {}

    async def fake_generate(
        self,
        *,
        user_id,
        request,
    ):
        captured["generate_user_id"] = user_id
        captured["generate_request"] = request

        return (
            CapabilityLearningCandidateGenerationResult(
                analyzed_reports=0,
                eligible_interpretations=0,
                created_candidates=0,
                existing_candidates=0,
                items=(),
            )
        )

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

    async def fake_review(
        self,
        **kwargs,
    ):
        captured["review"] = kwargs
        return None

    monkeypatch.setattr(
        CapabilityLearningInsightCandidateOperations,
        "generate",
        fake_generate,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightCandidateOperations,
        "list_latest",
        fake_list_latest,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightCandidateOperations,
        "get_latest",
        fake_get_latest,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightCandidateOperations,
        "history",
        fake_history,
    )
    monkeypatch.setattr(
        CapabilityLearningInsightCandidateOperations,
        "review",
        fake_review,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            generated = await client.post(
                "/capabilities/"
                "learning-insight-candidates/"
                "generate",
                json={
                    "tenant_id": "tenant-a",
                    "window_hours": 24,
                },
            )

            listed = await client.get(
                "/capabilities/"
                "learning-insight-candidates",
                params={
                    "tenant_id": "tenant-a",
                    "status": "validated",
                    "limit": 20,
                },
            )

            missing = await client.get(
                "/capabilities/"
                "learning-insight-candidates/"
                f"{candidate_id}"
            )

            history = await client.get(
                "/capabilities/"
                "learning-insight-candidates/"
                f"{candidate_id}/history"
            )

            reviewed = await client.post(
                "/capabilities/"
                "learning-insight-candidates/"
                f"{candidate_id}/review",
                json={
                    "decision": "approve",
                    "reason": "Confirmed.",
                },
            )

        assert generated.status_code == 201
        assert listed.status_code == 200
        assert missing.status_code == 404
        assert history.status_code == 404
        assert reviewed.status_code == 404

        assert captured[
            "generate_user_id"
        ] == user_id
        assert captured[
            "generate_request"
        ].tenant_id == "tenant-a"

        assert captured["list"]["user_id"] == (
            user_id
        )
        assert captured["list"]["tenant_id"] == (
            "tenant-a"
        )
        assert captured["list"]["status"] == (
            "validated"
        )

        assert captured["get"]["user_id"] == (
            user_id
        )
        assert captured[
            "get"
        ]["candidate_id"] == candidate_id

        assert captured[
            "history"
        ]["user_id"] == user_id

        assert captured[
            "review"
        ]["user_id"] == user_id
        assert captured[
            "review"
        ]["reviewed_by_user_id"] == user_id
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_review_validation_error_maps_to_422(
    monkeypatch,
):
    user_id = uuid4()

    async def fake_review(
        self,
        **kwargs,
    ):
        raise ValueError(
            "Only a pending validated candidate "
            "can be reviewed"
        )

    monkeypatch.setattr(
        CapabilityLearningInsightCandidateOperations,
        "review",
        fake_review,
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
                "learning-insight-candidates/"
                f"{uuid4()}/review",
                json={
                    "decision": "approve",
                    "reason": "Confirmed.",
                },
            )

        assert response.status_code == 422
        assert "pending validated" in (
            response.json()["detail"]
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
