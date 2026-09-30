from __future__ import annotations

from datetime import datetime, timedelta, timezone
import runpy
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.main import app
from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
)
from app.api.auth import get_current_user
from app.runtime.objectives.learning import (
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateRepository,
    ObjectiveLearningLifecycleOperations,
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


async def _seed_pending_candidate(
    *,
    user_id,
):
    helpers = _seed_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_resolution = helpers["_source_for_resolution"]
    summarize_one_experience = helpers["_summarize_one_experience"]
    static_source_loader = helpers["StaticCanonicalSourceLoader"]
    recording_service_type = helpers["CustomerSupportObjectiveLearningRecordingService"]
    experience_repository_type = helpers["ObjectiveLearningExperienceRepository"]

    base_source = canonical_source()

    async with SessionLocal() as db:
        resolution_record_id = await persist_resolution_parent(
            db,
            user_id=user_id,
            base_source=base_source,
        )

        source = source_for_resolution(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=(resolution_record_id),
        )

        experience_repository = experience_repository_type(db)

        recording = await recording_service_type(
            db,
            source_loader=static_source_loader(source),
            repository=experience_repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=(resolution_record_id),
        )

        proposed_at = datetime.now(timezone.utc) + timedelta(seconds=1)

        aggregation = await summarize_one_experience(
            db,
            user_id=user_id,
            experience_repository=(experience_repository),
            record=recording.record,
            now=proposed_at,
        )

        proposal = await _lifecycle(db).propose(
            user_id=user_id,
            aggregation=aggregation,
            proposed_at=proposed_at,
        )

        candidate = proposal.candidate

        assert candidate.candidate_version == 1
        assert candidate.status.value == "validated"
        assert candidate.approval_status.value == "pending"

        return candidate.candidate_id


@pytest.mark.asyncio
async def test_authenticated_review_approves_append_only_candidate():
    user_id = uuid4()
    other_user_id = uuid4()

    candidate_id = await _seed_pending_candidate(user_id=user_id)

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            approved_response = await client.post(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/reviews",
                json={
                    "decision": "approve",
                    "reason": ("Verified advisory evidence accepted by reviewer."),
                },
            )

            assert approved_response.status_code == 200

            approved = approved_response.json()

            assert approved["candidate_id"] == str(candidate_id)
            assert approved["candidate_version"] == 2
            assert approved["status"] == "approved"
            assert approved["approval_status"] == "approved"
            assert approved["reviewed_by_user_id"] == str(user_id)
            assert approved["review_reason"] == (
                "Verified advisory evidence accepted by reviewer."
            )

            assert approved["informational_only"] is True
            assert approved["affects_ranking"] is False
            assert approved["affects_capability_selection"] is False
            assert approved["affects_business_plan"] is False
            assert approved["selects_provider"] is False
            assert approved["authorizes_execution"] is False
            assert approved["bypasses_approval"] is False
            assert approved["bypasses_verification"] is False

            history = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/history"
            )

            assert history.status_code == 200
            assert [item["candidate_version"] for item in history.json()] == [1, 2]

            approved_insight = await client.get(
                f"/customer-service/objective-learning/approved-insights/{candidate_id}"
            )

            assert approved_insight.status_code == 200
            assert approved_insight.json()["provenance"]["candidate_version"] == 2

            # Terminal candidates cannot be reviewed again.
            repeated = await client.post(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/reviews",
                json={
                    "decision": "reject",
                    "reason": ("A second conflicting decision must not append."),
                },
            )

            assert repeated.status_code == 409
            assert repeated.json()["detail"] == (
                "Only a pending validated objective learning candidate can be reviewed"
            )

            invalid_decision = await client.post(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/reviews",
                json={
                    "decision": "invalid",
                    "reason": "Invalid enum.",
                },
            )

            assert invalid_decision.status_code == 422

            blank_reason = await client.post(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/reviews",
                json={
                    "decision": "approve",
                    "reason": "   ",
                },
            )

            assert blank_reason.status_code == 422

        async with SessionLocal() as verify_db:
            revision_count = await verify_db.scalar(
                select(func.count())
                .select_from(ObjectiveLearningCandidateRevisionRecord)
                .where(
                    ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                    ObjectiveLearningCandidateRevisionRecord.candidate_id
                    == candidate_id,
                )
            )

            assert revision_count == 2

        # -------------------------------------------------
        # Another authenticated user cannot review or infer
        # the candidate.
        # -------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: FakeUser(other_user_id)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            hidden = await client.post(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/reviews",
                json={
                    "decision": "approve",
                    "reason": ("Cross-user review must fail."),
                },
            )

            assert hidden.status_code == 404

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_authenticated_review_rejects_candidate():
    user_id = uuid4()

    candidate_id = await _seed_pending_candidate(user_id=user_id)

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            rejected_response = await client.post(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/reviews",
                json={
                    "decision": "reject",
                    "reason": ("Evidence is valid, but this guidance is unsuitable."),
                },
            )

            assert rejected_response.status_code == 200

            rejected = rejected_response.json()

            assert rejected["candidate_version"] == 2
            assert rejected["status"] == "rejected"
            assert rejected["approval_status"] == "rejected"
            assert rejected["blocking_reasons"] == ["approval_rejected"]
            assert rejected["reviewed_by_user_id"] == str(user_id)
            assert rejected["informational_only"] is True
            assert rejected["authorizes_execution"] is False

            approved_insight = await client.get(
                f"/customer-service/objective-learning/approved-insights/{candidate_id}"
            )

            assert approved_insight.status_code == 404

            history = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/history"
            )

            assert history.status_code == 200
            assert [item["status"] for item in history.json()] == [
                "validated",
                "rejected",
            ]

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
