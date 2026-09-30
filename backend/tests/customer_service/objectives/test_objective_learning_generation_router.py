from __future__ import annotations

import runpy
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_recording import (
    CustomerSupportObjectiveLearningRecordingService,
)
from app.main import app
from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
)
from app.api.auth import get_current_user
from app.runtime.objectives.learning import (
    ObjectiveLearningExperienceRepository,
)


class FakeUser:
    def __init__(self, user_id) -> None:
        self.id = user_id


def _seed_helpers():
    return runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_"
        "retry_recovery_e2e.py"
    )


@pytest.mark.asyncio
async def test_authenticated_generation_is_durable_and_idempotent():
    helpers = _seed_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_resolution = helpers["_source_for_resolution"]
    static_source_loader = helpers["StaticCanonicalSourceLoader"]

    user_id = uuid4()
    other_user_id = uuid4()

    base_source = canonical_source()

    async with SessionLocal() as setup_db:
        resolution_record_id = await persist_resolution_parent(
            setup_db,
            user_id=user_id,
            base_source=base_source,
        )

        source = source_for_resolution(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        repository = ObjectiveLearningExperienceRepository(setup_db)

        recording = await CustomerSupportObjectiveLearningRecordingService(
            setup_db,
            source_loader=static_source_loader(source),
            repository=repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        assert recording.created is True

        tenant_id = recording.record.tenant_id

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            ensured_policy = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert ensured_policy.status_code == 201
            assert ensured_policy.json()["created"] is True

            first = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "tenant_id": tenant_id,
                    "window_hours": 24,
                },
            )

            assert first.status_code == 201

            first_body = first.json()

            assert first_body["analyzed_summaries"] == 1
            assert first_body["created_candidates"] == 1
            assert first_body["existing_candidates"] == 0
            assert len(first_body["items"]) == 1

            first_item = first_body["items"][0]
            candidate = first_item["candidate"]

            assert first_item["created"] is True
            assert candidate["candidate_version"] == 1
            assert candidate["policy_ref"] == (
                "customer_service.support.objective_learning"
            )
            assert candidate["policy_version"] == 1

            assert candidate["informational_only"] is True
            assert candidate["affects_ranking"] is False
            assert candidate["affects_capability_selection"] is False
            assert candidate["affects_business_plan"] is False
            assert candidate["selects_provider"] is False
            assert candidate["authorizes_execution"] is False
            assert candidate["bypasses_approval"] is False
            assert candidate["bypasses_verification"] is False

            candidate_id = candidate["candidate_id"]

            repeated = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "tenant_id": tenant_id,
                    "window_hours": 24,
                },
            )

            assert repeated.status_code == 201

            repeated_body = repeated.json()

            assert repeated_body["analyzed_summaries"] == 1
            assert repeated_body["created_candidates"] == 0
            assert repeated_body["existing_candidates"] == 1
            assert len(repeated_body["items"]) == 1

            repeated_item = repeated_body["items"][0]

            assert repeated_item["created"] is False
            assert repeated_item["candidate"]["candidate_id"] == candidate_id
            assert repeated_item["candidate"]["candidate_version"] == 1

            invalid_window = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "window_hours": 0,
                },
            )

            assert invalid_window.status_code == 422

            forbidden_policy_override = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "tenant_id": tenant_id,
                    "window_hours": 24,
                    "policy_version": 999,
                },
            )

            assert forbidden_policy_override.status_code == 422

        async with SessionLocal() as verify_db:
            rows = list(
                (
                    await verify_db.execute(
                        select(ObjectiveLearningCandidateRevisionRecord).where(
                            ObjectiveLearningCandidateRevisionRecord.user_id == user_id
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert len(rows) == 1
            assert str(rows[0].candidate_id) == candidate_id
            assert rows[0].version == 1
            assert rows[0].policy_ref == ("customer_service.support.objective_learning")
            assert rows[0].policy_version == 1

            row_count = await verify_db.scalar(
                select(func.count())
                .select_from(ObjectiveLearningCandidateRevisionRecord)
                .where(ObjectiveLearningCandidateRevisionRecord.user_id == user_id)
            )

            assert row_count == 1

        # -----------------------------------------------------
        # Authenticated isolation: another user cannot generate
        # candidates from the first user's evidence.
        # -----------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: FakeUser(other_user_id)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            other_policy = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert other_policy.status_code == 201
            assert other_policy.json()["created"] is True

            hidden = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "tenant_id": tenant_id,
                    "window_hours": 24,
                },
            )

            assert hidden.status_code == 201
            assert hidden.json() == {
                "analyzed_summaries": 0,
                "created_candidates": 0,
                "existing_candidates": 0,
                "items": [],
            }

        async with SessionLocal() as verify_other_db:
            other_count = await verify_other_db.scalar(
                select(func.count())
                .select_from(ObjectiveLearningCandidateRevisionRecord)
                .where(
                    ObjectiveLearningCandidateRevisionRecord.user_id == other_user_id
                )
            )

            assert other_count == 0

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_generation_with_no_evidence_returns_empty_result():
    user_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            missing_policy = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={},
            )

            assert missing_policy.status_code == 409
            assert (
                "ensure the current policy before generation"
                in missing_policy.json()["detail"]
            )

            ensured_policy = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={},
            )

            assert ensured_policy.status_code == 201

            response = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={},
            )

            assert response.status_code == 201
            assert response.json() == {
                "analyzed_summaries": 0,
                "created_candidates": 0,
                "existing_candidates": 0,
                "items": [],
            }

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


def test_generation_route_precedes_candidate_uuid_route():
    objective_learning_routes = [
        route.path
        for route in app.routes
        if route.path.startswith("/customer-service/objective-learning/candidates")
    ]

    generation_index = objective_learning_routes.index(
        "/customer-service/objective-learning/candidates/generate"
    )
    detail_index = objective_learning_routes.index(
        "/customer-service/objective-learning/candidates/{candidate_id}"
    )

    assert generation_index < detail_index
