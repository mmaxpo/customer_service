from __future__ import annotations

import runpy
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_recording import (
    CustomerSupportObjectiveLearningRecordingService,
)
from app.main import app
from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
    ObjectiveLearningExperienceRecord,
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
async def test_objective_learning_full_http_to_postgres_lifecycle():
    """
    Prove one uninterrupted authenticated production path:

    verified resolution
      -> immutable experience persistence
      -> HTTP candidate generation
      -> HTTP candidate/history reads
      -> HTTP human approval
      -> HTTP approved-insight reads
      -> direct Postgres revision verification
      -> complete cross-user isolation

    The resulting insight remains informational and cannot authorize
    planning, provider selection, workflow behavior, or execution.
    """

    helpers = _seed_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_resolution = helpers["_source_for_resolution"]
    static_source_loader = helpers["StaticCanonicalSourceLoader"]

    user_id = uuid4()
    other_user_id = uuid4()

    base_source = canonical_source()

    # ---------------------------------------------------------
    # Persist the verified resolution and immutable experience.
    # ---------------------------------------------------------
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
        assert recording.experience.informational_only is True
        assert recording.experience.authorizes_execution is False

        experience_id = recording.record.id
        tenant_id = recording.record.tenant_id

        # A single high-confidence experience contributes an
        # effective sample size of 0.98, below the production
        # profile minimum of 1.0. Add a second independent
        # verified resolution in the same learning scope instead
        # of weakening any production policy threshold.
        # Objective-resolution persistence is idempotent by
        # authenticated owner, objective namespace, evaluation
        # reference/version, and projection version. Give the
        # second verified assessment a distinct evaluation identity
        # while preserving the same learning validity scope.
        second_base_source = base_source.model_copy(
            update={
                "evaluation_ref": (f"{base_source.evaluation_ref}:second"),
            }
        )

        assert second_base_source.evaluation_ref != base_source.evaluation_ref
        assert second_base_source.objective_namespace == base_source.objective_namespace
        assert second_base_source.objective_type == base_source.objective_type
        assert second_base_source.tenant_id == base_source.tenant_id

        second_resolution_record_id = await persist_resolution_parent(
            setup_db,
            user_id=user_id,
            base_source=second_base_source,
        )

        assert second_resolution_record_id != resolution_record_id

        second_source = source_for_resolution(
            base_source=second_base_source,
            user_id=user_id,
            resolution_record_id=second_resolution_record_id,
        )

        second_recording = await CustomerSupportObjectiveLearningRecordingService(
            setup_db,
            source_loader=static_source_loader(second_source),
            repository=repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=second_resolution_record_id,
        )

        assert second_recording.created is True
        assert second_recording.record.id != experience_id
        assert second_recording.record.tenant_id == tenant_id
        assert (
            second_recording.record.objective_namespace
            == recording.record.objective_namespace
        )
        assert second_recording.record.objective_type == recording.record.objective_type
        assert second_recording.record.profile_ref == recording.record.profile_ref
        assert (
            second_recording.record.profile_version == recording.record.profile_version
        )
        assert second_recording.experience.informational_only is True
        assert second_recording.experience.authorizes_execution is False

        second_experience_id = second_recording.record.id

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # -------------------------------------------------
            # Generate the deterministic candidate through HTTP.
            # -------------------------------------------------
            policy_response = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert policy_response.status_code == 201
            assert policy_response.json()["created"] is True

            durable_policy = policy_response.json()["revision"]

            assert durable_policy["policy_version"] == 1
            assert durable_policy["profile_version"] == 1
            assert durable_policy["informational_only"] is True
            assert durable_policy["authorizes_execution"] is False

            generated_response = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "tenant_id": tenant_id,
                    "window_hours": 24,
                },
            )

            assert generated_response.status_code == 201

            generated = generated_response.json()

            assert generated["analyzed_summaries"] == 1
            assert generated["created_candidates"] == 1
            assert generated["existing_candidates"] == 0
            assert len(generated["items"]) == 1

            generated_item = generated["items"][0]
            candidate = generated_item["candidate"]

            assert generated_item["created"] is True
            assert candidate["candidate_version"] == 1
            assert candidate["evidence"]["total_experiences"] == 2
            assert candidate["evidence"]["unique_resolution_count"] == 2
            assert (
                candidate["evidence"]["effective_sample_size"]
                >= candidate["evidence"]["minimum_effective_sample_size"]
            )
            assert candidate["evidence"]["evidence_sufficient"] is True
            assert candidate["status"] == "validated"
            assert candidate["approval_status"] == "pending"
            assert candidate["validation_passed"] is True

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

            # -------------------------------------------------
            # Read the generated candidate and version-1 history.
            # -------------------------------------------------
            candidate_detail = await client.get(
                f"/customer-service/objective-learning/candidates/{candidate_id}"
            )

            assert candidate_detail.status_code == 200
            assert candidate_detail.json() == candidate

            history_before_review = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/history"
            )

            assert history_before_review.status_code == 200
            assert [
                item["candidate_version"] for item in history_before_review.json()
            ] == [1]
            assert history_before_review.json()[0]["status"] == "validated"

            pending_insight = await client.get(
                f"/customer-service/objective-learning/approved-insights/{candidate_id}"
            )

            assert pending_insight.status_code == 404

            # -------------------------------------------------
            # Approve through the authenticated review endpoint.
            # -------------------------------------------------
            review_reason = (
                "Verified customer-support evidence approved "
                "through the complete HTTP lifecycle."
            )

            reviewed_response = await client.post(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/reviews",
                json={
                    "decision": "approve",
                    "reason": review_reason,
                },
            )

            assert reviewed_response.status_code == 200

            reviewed = reviewed_response.json()

            assert reviewed["candidate_id"] == candidate_id
            assert reviewed["candidate_version"] == 2
            assert reviewed["status"] == "approved"
            assert reviewed["approval_status"] == "approved"
            assert reviewed["validation_passed"] is True
            assert reviewed["reviewed_by_user_id"] == str(user_id)
            assert reviewed["review_reason"] == review_reason

            assert reviewed["informational_only"] is True
            assert reviewed["affects_ranking"] is False
            assert reviewed["affects_capability_selection"] is False
            assert reviewed["affects_business_plan"] is False
            assert reviewed["selects_provider"] is False
            assert reviewed["authorizes_execution"] is False
            assert reviewed["bypasses_approval"] is False
            assert reviewed["bypasses_verification"] is False

            # -------------------------------------------------
            # Read latest state, full history, and approved insight.
            # -------------------------------------------------
            latest_response = await client.get(
                f"/customer-service/objective-learning/candidates/{candidate_id}"
            )

            assert latest_response.status_code == 200
            assert latest_response.json() == reviewed

            history_response = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/history"
            )

            assert history_response.status_code == 200

            history = history_response.json()

            assert [item["candidate_version"] for item in history] == [1, 2]
            assert [item["status"] for item in history] == [
                "validated",
                "approved",
            ]
            assert history[0]["reviewed_at"] is None
            assert history[1] == reviewed

            insight_response = await client.get(
                f"/customer-service/objective-learning/approved-insights/{candidate_id}"
            )

            assert insight_response.status_code == 200

            insight = insight_response.json()

            assert insight["provenance"]["candidate_id"] == (candidate_id)
            assert insight["provenance"]["candidate_version"] == 2
            assert insight["decision"] == "approved"
            assert insight["recommended_review"] == review_reason

            assert insight["informational_only"] is True
            assert insight["affects_ranking"] is False
            assert insight["affects_capability_selection"] is False
            assert insight["affects_business_plan"] is False
            assert insight["selects_provider"] is False
            assert insight["authorizes_execution"] is False
            assert insight["bypasses_approval"] is False
            assert insight["bypasses_verification"] is False

            approved_list_response = await client.get(
                "/customer-service/objective-learning/approved-insights",
                params={
                    "tenant_id": tenant_id,
                    "objective_namespace": (recording.record.objective_namespace),
                    "objective_type": (recording.record.objective_type),
                    "profile_ref": (recording.record.profile_ref),
                    "profile_version": (recording.record.profile_version),
                },
            )

            assert approved_list_response.status_code == 200

            approved_list = approved_list_response.json()

            assert approved_list["count"] == 1
            assert (
                approved_list["items"][0]["provenance"]["candidate_id"] == candidate_id
            )

        # -----------------------------------------------------
        # Verify the exact durable rows directly in Postgres.
        # -----------------------------------------------------
        async with SessionLocal() as verify_db:
            experience_rows = list(
                (
                    await verify_db.execute(
                        select(ObjectiveLearningExperienceRecord).where(
                            ObjectiveLearningExperienceRecord.user_id == user_id,
                            ObjectiveLearningExperienceRecord.id == experience_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert len(experience_rows) == 1

            experience_row = experience_rows[0]

            assert experience_row.resolution_record_id == resolution_record_id
            assert experience_row.informational_only is True
            assert experience_row.authorizes_execution is False

            second_experience_rows = list(
                (
                    await verify_db.execute(
                        select(ObjectiveLearningExperienceRecord).where(
                            ObjectiveLearningExperienceRecord.user_id == user_id,
                            ObjectiveLearningExperienceRecord.id
                            == second_experience_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert len(second_experience_rows) == 1

            second_experience_row = second_experience_rows[0]

            assert (
                second_experience_row.resolution_record_id
                == second_resolution_record_id
            )
            assert second_experience_row.informational_only is True
            assert second_experience_row.authorizes_execution is False

            all_experience_rows = list(
                (
                    await verify_db.execute(
                        select(ObjectiveLearningExperienceRecord).where(
                            ObjectiveLearningExperienceRecord.user_id == user_id,
                            ObjectiveLearningExperienceRecord.id.in_(
                                (
                                    experience_id,
                                    second_experience_id,
                                )
                            ),
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert {row.id for row in all_experience_rows} == {
                experience_id,
                second_experience_id,
            }
            assert {row.resolution_record_id for row in all_experience_rows} == {
                resolution_record_id,
                second_resolution_record_id,
            }

            revision_rows = list(
                (
                    await verify_db.execute(
                        select(ObjectiveLearningCandidateRevisionRecord)
                        .where(
                            ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                            ObjectiveLearningCandidateRevisionRecord.candidate_id
                            == candidate_id,
                        )
                        .order_by(
                            ObjectiveLearningCandidateRevisionRecord.version.asc()
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert len(revision_rows) == 2
            assert [row.version for row in revision_rows] == [1, 2]
            assert [row.status for row in revision_rows] == [
                "validated",
                "approved",
            ]
            assert [row.approval_status for row in revision_rows] == [
                "pending",
                "approved",
            ]

            assert all(
                row.policy_ref == ("customer_service.support.objective_learning")
                for row in revision_rows
            )
            assert all(row.policy_version == 1 for row in revision_rows)

            # These two safety boundaries are dedicated database
            # columns for direct filtering and integrity checks.
            assert all(row.informational_only is True for row in revision_rows)
            assert all(row.authorizes_execution is False for row in revision_rows)

            # The complete immutable candidate snapshot is stored
            # in candidate_json and is the repository's canonical
            # deserialization source for every revision.
            persisted_candidates = [row.candidate_json for row in revision_rows]

            assert [item["candidate_version"] for item in persisted_candidates] == [
                1,
                2,
            ]
            assert [item["status"] for item in persisted_candidates] == [
                "validated",
                "approved",
            ]
            assert [item["approval_status"] for item in persisted_candidates] == [
                "pending",
                "approved",
            ]

            for persisted in persisted_candidates:
                assert persisted["informational_only"] is True
                assert persisted["affects_ranking"] is False
                assert persisted["affects_capability_selection"] is False
                assert persisted["affects_business_plan"] is False
                assert persisted["selects_provider"] is False
                assert persisted["authorizes_execution"] is False
                assert persisted["bypasses_approval"] is False
                assert persisted["bypasses_verification"] is False

            assert persisted_candidates[0]["reviewed_at"] is None
            assert persisted_candidates[1]["reviewed_by_user_id"] == str(user_id)
            assert persisted_candidates[1]["review_reason"] == review_reason

        # -----------------------------------------------------
        # Another authenticated user cannot infer any part of
        # the first user's learning lifecycle.
        # -----------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: FakeUser(other_user_id)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            hidden_experience = await client.get(
                f"/customer-service/objective-learning/experiences/{experience_id}"
            )
            assert hidden_experience.status_code == 404

            hidden_second_experience = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"experiences/{second_experience_id}"
            )
            assert hidden_second_experience.status_code == 404

            hidden_generation = await client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "tenant_id": tenant_id,
                    "window_hours": 24,
                },
            )

            assert hidden_generation.status_code == 409
            assert hidden_generation.json()["detail"] == (
                "Durable customer-support objective-learning policy "
                "not found; ensure the current policy before generation"
            )

            hidden_candidate = await client.get(
                f"/customer-service/objective-learning/candidates/{candidate_id}"
            )
            assert hidden_candidate.status_code == 404

            hidden_history = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/history"
            )
            assert hidden_history.status_code == 404

            hidden_review = await client.post(
                "/customer-service/"
                "objective-learning/"
                f"candidates/{candidate_id}/reviews",
                json={
                    "decision": "approve",
                    "reason": ("Cross-user lifecycle access must remain hidden."),
                },
            )
            assert hidden_review.status_code == 404

            hidden_insight = await client.get(
                f"/customer-service/objective-learning/approved-insights/{candidate_id}"
            )
            assert hidden_insight.status_code == 404

            hidden_approved_list = await client.get(
                "/customer-service/objective-learning/approved-insights",
                params={
                    "tenant_id": tenant_id,
                    "objective_namespace": (recording.record.objective_namespace),
                    "objective_type": (recording.record.objective_type),
                },
            )

            assert hidden_approved_list.status_code == 200
            assert hidden_approved_list.json()["count"] == 0
            assert hidden_approved_list.json()["items"] == []

        async with SessionLocal() as verify_other_db:
            other_experiences = list(
                (
                    await verify_other_db.execute(
                        select(ObjectiveLearningExperienceRecord).where(
                            ObjectiveLearningExperienceRecord.user_id == other_user_id
                        )
                    )
                )
                .scalars()
                .all()
            )

            other_revisions = list(
                (
                    await verify_other_db.execute(
                        select(ObjectiveLearningCandidateRevisionRecord).where(
                            ObjectiveLearningCandidateRevisionRecord.user_id
                            == other_user_id
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert other_experiences == []
            assert other_revisions == []

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
