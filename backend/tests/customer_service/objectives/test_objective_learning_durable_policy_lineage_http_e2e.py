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
    ObjectiveLearningPolicyRevisionRecord,
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
async def test_durable_policy_lineage_survives_fresh_http_and_database_sessions():
    """
    Prove the complete HTTP-D5 durable lineage boundary:

    authenticated HTTP policy ensure
      -> committed PostgreSQL policy revision
      -> first HTTP client/session closes
      -> fresh HTTP client and database dependency
      -> generation resolves the exact persisted profile snapshot
      -> candidate persists the exact policy reference and version
      -> policy history remains readable
      -> another authenticated user cannot read or consume owner lineage

    The generated candidate remains informational and cannot authorize
    planning, ranking, provider selection, workflow behavior, or execution.
    """

    helpers = _seed_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_resolution = helpers["_source_for_resolution"]
    static_source_loader = helpers["StaticCanonicalSourceLoader"]

    owner_id = uuid4()
    other_user_id = uuid4()

    base_source = canonical_source()

    # Two independent verified experiences are required by the real
    # production effective-sample-size threshold. Do not weaken policy.
    async with SessionLocal() as setup_db:
        repository = ObjectiveLearningExperienceRepository(setup_db)

        first_resolution_id = await persist_resolution_parent(
            setup_db,
            user_id=owner_id,
            base_source=base_source,
        )

        first_source = source_for_resolution(
            base_source=base_source,
            user_id=owner_id,
            resolution_record_id=first_resolution_id,
        )

        first_recording = await CustomerSupportObjectiveLearningRecordingService(
            setup_db,
            source_loader=static_source_loader(first_source),
            repository=repository,
        ).record_for_resolution(
            user_id=owner_id,
            resolution_record_id=first_resolution_id,
        )

        second_base_source = base_source.model_copy(
            update={
                "evaluation_ref": f"{base_source.evaluation_ref}:http-d5-second",
            }
        )

        second_resolution_id = await persist_resolution_parent(
            setup_db,
            user_id=owner_id,
            base_source=second_base_source,
        )

        second_source = source_for_resolution(
            base_source=second_base_source,
            user_id=owner_id,
            resolution_record_id=second_resolution_id,
        )

        second_recording = await CustomerSupportObjectiveLearningRecordingService(
            setup_db,
            source_loader=static_source_loader(second_source),
            repository=repository,
        ).record_for_resolution(
            user_id=owner_id,
            resolution_record_id=second_resolution_id,
        )

        assert first_recording.created is True
        assert second_recording.created is True
        assert first_recording.record.id != second_recording.record.id
        assert first_recording.record.tenant_id == second_recording.record.tenant_id

        tenant_id = first_recording.record.tenant_id

    app.dependency_overrides[get_current_user] = lambda: FakeUser(owner_id)

    try:
        # -------------------------------------------------------------
        # First authenticated HTTP lifecycle: ensure the server-owned
        # policy and then close the client/session boundary completely.
        # -------------------------------------------------------------
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ensure_client:
            ensured_response = await ensure_client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert ensured_response.status_code == 201

            ensured = ensured_response.json()

            assert ensured["created"] is True

            durable_policy = ensured["revision"]
            policy_revision_id = durable_policy["id"]
            policy_ref = durable_policy["policy_ref"]
            policy_version = durable_policy["policy_version"]

            assert durable_policy["user_id"] == str(owner_id)
            assert durable_policy["tenant_id"] == tenant_id
            assert policy_version == 1
            assert durable_policy["enabled"] is True
            assert durable_policy["informational_only"] is True
            assert durable_policy["authorizes_execution"] is False

        # -------------------------------------------------------------
        # Direct PostgreSQL proof after the ensure HTTP client closes.
        # This is a new independent SQLAlchemy session.
        # -------------------------------------------------------------
        async with SessionLocal() as policy_verify_db:
            persisted_policy = await policy_verify_db.get(
                ObjectiveLearningPolicyRevisionRecord,
                policy_revision_id,
            )

            assert persisted_policy is not None
            assert persisted_policy.user_id == owner_id
            assert persisted_policy.tenant_id == tenant_id
            assert persisted_policy.policy_ref == policy_ref
            assert persisted_policy.policy_version == policy_version
            assert persisted_policy.profile_json == durable_policy["profile"]
            assert persisted_policy.enabled is True
            assert persisted_policy.informational_only is True
            assert persisted_policy.authorizes_execution is False

        # -------------------------------------------------------------
        # Fresh HTTP client. FastAPI creates a fresh get_db dependency
        # session; generation must reconstruct policy from PostgreSQL.
        # -------------------------------------------------------------
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as generation_client:
            generated_response = await generation_client.post(
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
            assert candidate["policy_ref"] == policy_ref
            assert candidate["policy_version"] == policy_version
            assert candidate["informational_only"] is True
            assert candidate["affects_ranking"] is False
            assert candidate["affects_capability_selection"] is False
            assert candidate["affects_business_plan"] is False
            assert candidate["selects_provider"] is False
            assert candidate["authorizes_execution"] is False
            assert candidate["bypasses_approval"] is False
            assert candidate["bypasses_verification"] is False

            candidate_id = candidate["candidate_id"]

            current_policy_response = await generation_client.get(
                "/customer-service/objective-learning/policies/current",
                params={"tenant_id": tenant_id},
            )
            assert current_policy_response.status_code == 200
            assert current_policy_response.json() == durable_policy

            exact_policy_response = await generation_client.get(
                f"/customer-service/objective-learning/policies/{policy_version}",
                params={"tenant_id": tenant_id},
            )
            assert exact_policy_response.status_code == 200
            assert exact_policy_response.json() == durable_policy

            history_response = await generation_client.get(
                "/customer-service/objective-learning/policies",
                params={"tenant_id": tenant_id},
            )
            assert history_response.status_code == 200
            assert history_response.json() == {
                "items": [durable_policy],
                "count": 1,
                "limit": 100,
                "offset": 0,
            }

        # -------------------------------------------------------------
        # Fresh direct PostgreSQL session proves the candidate persisted
        # exactly the durable policy lineage resolved during generation.
        # -------------------------------------------------------------
        async with SessionLocal() as candidate_verify_db:
            candidate_rows = list(
                (
                    await candidate_verify_db.execute(
                        select(ObjectiveLearningCandidateRevisionRecord).where(
                            ObjectiveLearningCandidateRevisionRecord.user_id
                            == owner_id,
                            ObjectiveLearningCandidateRevisionRecord.candidate_id
                            == candidate_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert len(candidate_rows) == 1

            candidate_row = candidate_rows[0]

            assert candidate_row.version == 1
            assert candidate_row.policy_ref == policy_ref
            assert candidate_row.policy_version == policy_version
            assert candidate_row.informational_only is True
            assert candidate_row.authorizes_execution is False
            assert candidate_row.candidate_json["policy_ref"] == policy_ref
            assert candidate_row.candidate_json["policy_version"] == policy_version
            assert candidate_row.candidate_json == candidate

            policy_rows = list(
                (
                    await candidate_verify_db.execute(
                        select(ObjectiveLearningPolicyRevisionRecord).where(
                            ObjectiveLearningPolicyRevisionRecord.user_id == owner_id,
                            ObjectiveLearningPolicyRevisionRecord.tenant_id
                            == tenant_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert len(policy_rows) == 1
            assert str(policy_rows[0].id) == policy_revision_id
            assert policy_rows[0].policy_ref == candidate_row.policy_ref
            assert policy_rows[0].policy_version == candidate_row.policy_version

        # -------------------------------------------------------------
        # Another authenticated user cannot read or consume the owner's
        # durable policy, even while supplying the same tenant_id.
        # -------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: FakeUser(other_user_id)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as other_user_client:
            hidden_current = await other_user_client.get(
                "/customer-service/objective-learning/policies/current",
                params={"tenant_id": tenant_id},
            )
            assert hidden_current.status_code == 404

            hidden_exact = await other_user_client.get(
                f"/customer-service/objective-learning/policies/{policy_version}",
                params={"tenant_id": tenant_id},
            )
            assert hidden_exact.status_code == 404

            hidden_history = await other_user_client.get(
                "/customer-service/objective-learning/policies",
                params={"tenant_id": tenant_id},
            )
            assert hidden_history.status_code == 200
            assert hidden_history.json() == {
                "items": [],
                "count": 0,
                "limit": 100,
                "offset": 0,
            }

            hidden_generation = await other_user_client.post(
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

            hidden_candidate = await other_user_client.get(
                f"/customer-service/objective-learning/candidates/{candidate_id}"
            )
            assert hidden_candidate.status_code == 404

        async with SessionLocal() as other_user_verify_db:
            other_policy_rows = list(
                (
                    await other_user_verify_db.execute(
                        select(ObjectiveLearningPolicyRevisionRecord).where(
                            ObjectiveLearningPolicyRevisionRecord.user_id
                            == other_user_id,
                            ObjectiveLearningPolicyRevisionRecord.tenant_id
                            == tenant_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

            other_candidate_rows = list(
                (
                    await other_user_verify_db.execute(
                        select(ObjectiveLearningCandidateRevisionRecord).where(
                            ObjectiveLearningCandidateRevisionRecord.user_id
                            == other_user_id
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert other_policy_rows == []
            assert other_candidate_rows == []

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
