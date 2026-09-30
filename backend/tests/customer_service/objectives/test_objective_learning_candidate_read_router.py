from __future__ import annotations

from datetime import datetime, timedelta, timezone
import runpy
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.api.auth import get_current_user
from app.runtime.objectives.learning import (
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateRepository,
    ObjectiveLearningCandidateReviewRequest,
    ObjectiveLearningLifecycleOperations,
    ObjectiveLearningReviewDecision,
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


def _lifecycle(db):
    return ObjectiveLearningLifecycleOperations(
        db=db,
        repository=(ObjectiveLearningCandidateRepository(db)),
        factory=ObjectiveLearningCandidateFactory(
            policy=ObjectiveLearningCandidatePolicy(
                minimum_summary_confidence=0.0,
            )
        ),
    )


@pytest.mark.asyncio
async def test_authenticated_candidate_and_approved_insight_reads():
    helpers = _seed_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_resolution = helpers["_source_for_resolution"]
    summarize_one_experience = helpers["_summarize_one_experience"]
    static_source_loader = helpers["StaticCanonicalSourceLoader"]
    recording_service_type = helpers["CustomerSupportObjectiveLearningRecordingService"]
    experience_repository_type = helpers["ObjectiveLearningExperienceRepository"]

    user_id = uuid4()
    reviewer_id = uuid4()
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
            resolution_record_id=(resolution_record_id),
        )

        experience_repository = experience_repository_type(setup_db)

        recording = await recording_service_type(
            setup_db,
            source_loader=static_source_loader(source),
            repository=experience_repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=(resolution_record_id),
        )

        aggregation_now = datetime.now(timezone.utc) + timedelta(seconds=1)

        aggregation = await summarize_one_experience(
            setup_db,
            user_id=user_id,
            experience_repository=(experience_repository),
            record=recording.record,
            now=aggregation_now,
        )

        lifecycle = _lifecycle(setup_db)

        proposed = await lifecycle.propose(
            user_id=user_id,
            aggregation=aggregation,
            proposed_at=aggregation_now,
        )

        candidate_id = proposed.candidate.candidate_id

        approved = await lifecycle.review(
            user_id=user_id,
            candidate_id=candidate_id,
            reviewed_by_user_id=reviewer_id,
            request=(
                ObjectiveLearningCandidateReviewRequest(
                    decision=(ObjectiveLearningReviewDecision.APPROVE),
                    reason=("Approved for advisory read API test."),
                    reviewed_at=(aggregation_now + timedelta(seconds=1)),
                )
            ),
        )

        assert approved is not None

        scope_params = {
            "tenant_id": (aggregation.tenant_id),
            "objective_namespace": (aggregation.objective_namespace),
            "objective_type": (aggregation.objective_type),
            "objective_version": (aggregation.objective_version),
            "schema_ref": (aggregation.schema_ref),
            "profile_ref": (aggregation.profile_ref),
            "profile_version": (aggregation.profile_version),
            "extractor_ref": (aggregation.extractor_ref),
            "extractor_version": (aggregation.extractor_version),
        }

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            candidates = await client.get(
                "/customer-service/objective-learning/candidates",
                params=scope_params,
            )

            assert candidates.status_code == 200

            candidates_body = candidates.json()

            assert candidates_body["count"] == 1
            assert candidates_body["limit"] == 100
            assert candidates_body["offset"] == 0

            candidate_body = candidates_body["items"][0]

            assert candidate_body["candidate_id"] == str(candidate_id)
            assert candidate_body["candidate_version"] == 2
            assert candidate_body["status"] == "approved"
            assert candidate_body["approval_status"] == "approved"
            assert candidate_body["informational_only"] is True
            assert candidate_body["authorizes_execution"] is False

            filtered = await client.get(
                "/customer-service/objective-learning/candidates",
                params={
                    **scope_params,
                    "status": "approved",
                    "approval_status": "approved",
                    "validation_passed": True,
                },
            )

            assert filtered.status_code == 200
            assert filtered.json()["count"] == 1

            paged_out = await client.get(
                "/customer-service/objective-learning/candidates",
                params={
                    **scope_params,
                    "limit": 1,
                    "offset": 1,
                },
            )

            assert paged_out.status_code == 200
            assert paged_out.json()["items"] == []
            assert paged_out.json()["count"] == 0

            detail = await client.get(
                f"/customer-service/objective-learning/candidates/{candidate_id}"
            )

            assert detail.status_code == 200
            assert detail.json()["candidate_version"] == 2

            history = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/history"
            )

            assert history.status_code == 200
            assert [item["candidate_version"] for item in history.json()] == [1, 2]
            assert history.json()[0]["status"] == "validated"
            assert history.json()[1]["status"] == "approved"

            approved_list = await client.get(
                "/customer-service/objective-learning/approved-insights",
                params=scope_params,
            )

            assert approved_list.status_code == 200

            approved_list_body = approved_list.json()

            assert approved_list_body["count"] == 1

            insight = approved_list_body["items"][0]

            assert insight["provenance"]["candidate_id"] == str(candidate_id)
            assert insight["provenance"]["candidate_version"] == 2
            assert insight["informational_only"] is True
            assert insight["affects_ranking"] is False
            assert insight["affects_capability_selection"] is False
            assert insight["affects_business_plan"] is False
            assert insight["selects_provider"] is False
            assert insight["authorizes_execution"] is False
            assert insight["bypasses_approval"] is False
            assert insight["bypasses_verification"] is False

            approved_detail = await client.get(
                f"/customer-service/objective-learning/approved-insights/{candidate_id}"
            )

            assert approved_detail.status_code == 200
            assert approved_detail.json() == insight

            invalid_limit = await client.get(
                "/customer-service/objective-learning/candidates",
                params={"limit": 0},
            )

            assert invalid_limit.status_code == 422

        # -------------------------------------------------
        # Cross-user isolation.
        # -------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: FakeUser(other_user_id)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            hidden_candidates = await client.get(
                "/customer-service/objective-learning/candidates",
                params=scope_params,
            )

            assert hidden_candidates.status_code == 200
            assert hidden_candidates.json()["items"] == []
            assert hidden_candidates.json()["count"] == 0

            hidden_detail = await client.get(
                f"/customer-service/objective-learning/candidates/{candidate_id}"
            )

            assert hidden_detail.status_code == 404

            hidden_history = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/history"
            )

            assert hidden_history.status_code == 404

            hidden_approved = await client.get(
                "/customer-service/objective-learning/approved-insights",
                params=scope_params,
            )

            assert hidden_approved.status_code == 200
            assert hidden_approved.json()["items"] == []
            assert hidden_approved.json()["count"] == 0

            hidden_approved_detail = await client.get(
                f"/customer-service/objective-learning/approved-insights/{candidate_id}"
            )

            assert hidden_approved_detail.status_code == 404

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
