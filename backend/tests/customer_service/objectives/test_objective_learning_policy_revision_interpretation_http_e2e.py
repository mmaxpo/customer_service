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
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
    build_customer_support_objective_learning_profile,
)
from app.main import app
from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
    ObjectiveLearningPolicyRevisionRecord,
)
from app.api.auth import get_current_user
from app.runtime.objectives.learning import (
    ObjectiveLearningExperienceRepository,
    ObjectiveLearningPolicyRepository,
    ObjectiveLearningPolicyScope,
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
async def test_same_evidence_is_reinterpreted_by_immutable_policy_revisions():
    """
    Prove the HTTP-E policy interpretation lifecycle:

    same immutable verified evidence
      -> strict durable policy revision 1
      -> blocked immutable candidate under policy version 1
      -> append relaxed durable policy revision 2
      -> same evidence qualifies under policy version 2
      -> policy-aware identity produces a distinct candidate
      -> both policy snapshots and candidate interpretations remain
         historically reconstructable

    A threshold-only policy revision retains profile_version=1 because the
    extraction schema and evidence validity scope have not changed.

    Both interpretations remain informational and cannot authorize planning,
    ranking, provider selection, workflow behavior, or execution.
    """

    helpers = _seed_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_resolution = helpers["_source_for_resolution"]
    static_source_loader = helpers["StaticCanonicalSourceLoader"]

    user_id = uuid4()
    base_source = canonical_source()

    # -----------------------------------------------------------------
    # Persist two independent verified experiences under profile v1.
    # Their combined effective sample size is enough for relaxed policy
    # v2 (minimum 1.0), but not strict policy v1 (minimum 5.0).
    # -----------------------------------------------------------------
    async with SessionLocal() as setup_db:
        experience_repository = ObjectiveLearningExperienceRepository(setup_db)

        first_resolution_id = await persist_resolution_parent(
            setup_db,
            user_id=user_id,
            base_source=base_source,
        )

        first_source = source_for_resolution(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=first_resolution_id,
        )

        first_recording = await CustomerSupportObjectiveLearningRecordingService(
            setup_db,
            source_loader=static_source_loader(first_source),
            repository=experience_repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=first_resolution_id,
        )

        second_base_source = base_source.model_copy(
            update={
                "evaluation_ref": (
                    f"{base_source.evaluation_ref}:http-e-policy-revision"
                ),
            }
        )

        second_resolution_id = await persist_resolution_parent(
            setup_db,
            user_id=user_id,
            base_source=second_base_source,
        )

        second_source = source_for_resolution(
            base_source=second_base_source,
            user_id=user_id,
            resolution_record_id=second_resolution_id,
        )

        second_recording = await CustomerSupportObjectiveLearningRecordingService(
            setup_db,
            source_loader=static_source_loader(second_source),
            repository=experience_repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=second_resolution_id,
        )

        assert first_recording.created is True
        assert second_recording.created is True
        assert first_recording.record.profile_version == 1
        assert second_recording.record.profile_version == 1
        assert first_recording.record.tenant_id == second_recording.record.tenant_id

        tenant_id = first_recording.record.tenant_id

    scope = ObjectiveLearningPolicyScope(
        user_id=user_id,
        tenant_id=tenant_id,
        objective_namespace=CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
        objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
        profile_ref=CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
        policy_ref=CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    )

    strict_profile = build_customer_support_objective_learning_profile(
        profile_version=1,
        policy_version=1,
        minimum_confidence=0.90,
        minimum_effective_sample_size=5.0,
    )

    relaxed_profile = build_customer_support_objective_learning_profile(
        profile_version=1,
        policy_version=2,
        minimum_confidence=0.90,
        minimum_effective_sample_size=1.0,
    )

    assert strict_profile.profile_version == relaxed_profile.profile_version == 1
    assert strict_profile.qualification_policy.policy_version == 1
    assert relaxed_profile.qualification_policy.policy_version == 2

    # -----------------------------------------------------------------
    # Trusted server-side composition appends strict immutable policy v1.
    # Public clients cannot submit policy thresholds or policy versions.
    # -----------------------------------------------------------------
    async with SessionLocal() as strict_policy_db:
        policy_repository = ObjectiveLearningPolicyRepository(strict_policy_db)

        strict_row = await policy_repository.append_revision(
            scope=scope,
            profile=strict_profile,
            reason="HTTP-E strict evidence qualification policy",
            created_by_user_id=user_id,
        )

        await strict_policy_db.commit()

        strict_policy_id = strict_row.id

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        # -----------------------------------------------------------------
        # HTTP generation resolves strict policy v1 from PostgreSQL.
        # The interpretation is persisted but blocked by insufficient sample.
        # -----------------------------------------------------------------
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as strict_client:
            strict_generation_response = await strict_client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "tenant_id": tenant_id,
                    "window_hours": 24,
                },
            )

            assert strict_generation_response.status_code == 201

            strict_generation = strict_generation_response.json()

            assert strict_generation["analyzed_summaries"] == 1
            assert strict_generation["created_candidates"] == 1
            assert strict_generation["existing_candidates"] == 0
            assert len(strict_generation["items"]) == 1

            strict_item = strict_generation["items"][0]
            strict_candidate = strict_item["candidate"]

            assert strict_item["created"] is True
            assert strict_candidate["policy_ref"] == (
                CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF
            )
            assert strict_candidate["policy_version"] == 1
            assert strict_candidate["evidence"]["profile_version"] == 1
            assert strict_candidate["evidence"]["total_experiences"] == 2
            assert strict_candidate["evidence"]["minimum_effective_sample_size"] == 5.0
            assert strict_candidate["evidence"]["evidence_sufficient"] is False
            assert strict_candidate["validation_passed"] is False
            assert strict_candidate["status"] == "blocked"
            assert strict_candidate["approval_status"] == "not_required"
            assert strict_candidate["blocking_reasons"] == [
                "evidence_sufficient",
                "summary_confidence",
            ]

            assert strict_candidate["informational_only"] is True
            assert strict_candidate["affects_ranking"] is False
            assert strict_candidate["affects_capability_selection"] is False
            assert strict_candidate["affects_business_plan"] is False
            assert strict_candidate["selects_provider"] is False
            assert strict_candidate["authorizes_execution"] is False
            assert strict_candidate["bypasses_approval"] is False
            assert strict_candidate["bypasses_verification"] is False

            strict_candidate_id = strict_candidate["candidate_id"]

            strict_current_response = await strict_client.get(
                "/customer-service/objective-learning/policies/current",
                params={"tenant_id": tenant_id},
            )

            assert strict_current_response.status_code == 200
            assert strict_current_response.json()["id"] == str(strict_policy_id)
            assert strict_current_response.json()["profile_version"] == 1
            assert strict_current_response.json()["policy_version"] == 1
            assert (
                strict_current_response.json()["profile"]["qualification_policy"][
                    "minimum_effective_sample_size"
                ]
                == 5.0
            )

        # -----------------------------------------------------------------
        # Append policy v2 without changing profile_version. The extraction
        # contract and evidence scope are unchanged; only interpretation
        # thresholds change.
        # -----------------------------------------------------------------
        async with SessionLocal() as relaxed_policy_db:
            policy_repository = ObjectiveLearningPolicyRepository(relaxed_policy_db)

            relaxed_row = await policy_repository.append_revision(
                scope=scope,
                profile=relaxed_profile,
                reason="HTTP-E reviewed relaxed evidence qualification policy",
                created_by_user_id=user_id,
            )

            await relaxed_policy_db.commit()

            relaxed_policy_id = relaxed_row.id

        assert relaxed_policy_id != strict_policy_id

        # -----------------------------------------------------------------
        # A fresh HTTP request resolves latest policy v2 and reinterprets the
        # same immutable experiences. Policy-aware identity creates a new
        # candidate instead of overwriting or mutating the blocked candidate.
        # -----------------------------------------------------------------
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as relaxed_client:
            relaxed_generation_response = await relaxed_client.post(
                "/customer-service/objective-learning/candidates/generate",
                json={
                    "tenant_id": tenant_id,
                    "window_hours": 24,
                },
            )

            assert relaxed_generation_response.status_code == 201

            relaxed_generation = relaxed_generation_response.json()

            assert relaxed_generation["analyzed_summaries"] == 1
            assert relaxed_generation["created_candidates"] == 1
            assert relaxed_generation["existing_candidates"] == 0
            assert len(relaxed_generation["items"]) == 1

            relaxed_item = relaxed_generation["items"][0]
            relaxed_candidate = relaxed_item["candidate"]

            assert relaxed_item["created"] is True
            assert relaxed_candidate["policy_ref"] == (
                CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF
            )
            assert relaxed_candidate["policy_version"] == 2
            assert relaxed_candidate["evidence"]["profile_version"] == 1
            assert relaxed_candidate["evidence"]["total_experiences"] == 2
            assert relaxed_candidate["evidence"]["minimum_effective_sample_size"] == 1.0
            assert relaxed_candidate["evidence"]["evidence_sufficient"] is True
            assert relaxed_candidate["validation_passed"] is True
            assert relaxed_candidate["status"] == "validated"
            assert relaxed_candidate["approval_status"] == "pending"
            assert relaxed_candidate["blocking_reasons"] == [
                "explicit_approval_required",
            ]

            assert relaxed_candidate["informational_only"] is True
            assert relaxed_candidate["affects_ranking"] is False
            assert relaxed_candidate["affects_capability_selection"] is False
            assert relaxed_candidate["affects_business_plan"] is False
            assert relaxed_candidate["selects_provider"] is False
            assert relaxed_candidate["authorizes_execution"] is False
            assert relaxed_candidate["bypasses_approval"] is False
            assert relaxed_candidate["bypasses_verification"] is False

            relaxed_candidate_id = relaxed_candidate["candidate_id"]

            assert relaxed_candidate_id != strict_candidate_id

            current_response = await relaxed_client.get(
                "/customer-service/objective-learning/policies/current",
                params={"tenant_id": tenant_id},
            )

            assert current_response.status_code == 200

            current_policy = current_response.json()

            assert current_policy["id"] == str(relaxed_policy_id)
            assert current_policy["profile_version"] == 1
            assert current_policy["policy_version"] == 2
            assert (
                current_policy["profile"]["qualification_policy"][
                    "minimum_effective_sample_size"
                ]
                == 1.0
            )

            strict_exact_response = await relaxed_client.get(
                "/customer-service/objective-learning/policies/1",
                params={"tenant_id": tenant_id},
            )
            assert strict_exact_response.status_code == 200

            strict_exact = strict_exact_response.json()

            assert strict_exact["id"] == str(strict_policy_id)
            assert strict_exact["profile_version"] == 1
            assert strict_exact["policy_version"] == 1
            assert (
                strict_exact["profile"]["qualification_policy"][
                    "minimum_effective_sample_size"
                ]
                == 5.0
            )

            relaxed_exact_response = await relaxed_client.get(
                "/customer-service/objective-learning/policies/2",
                params={"tenant_id": tenant_id},
            )
            assert relaxed_exact_response.status_code == 200
            assert relaxed_exact_response.json() == current_policy

            policy_history_response = await relaxed_client.get(
                "/customer-service/objective-learning/policies",
                params={"tenant_id": tenant_id},
            )

            assert policy_history_response.status_code == 200

            policy_history = policy_history_response.json()

            assert policy_history["count"] == 2
            assert [item["policy_version"] for item in policy_history["items"]] == [
                2,
                1,
            ]
            assert [item["profile_version"] for item in policy_history["items"]] == [
                1,
                1,
            ]

            strict_candidate_response = await relaxed_client.get(
                f"/customer-service/objective-learning/candidates/{strict_candidate_id}"
            )
            assert strict_candidate_response.status_code == 200
            assert strict_candidate_response.json() == strict_candidate

            relaxed_candidate_response = await relaxed_client.get(
                f"/customer-service/objective-learning/candidates/{relaxed_candidate_id}"
            )
            assert relaxed_candidate_response.status_code == 200
            assert relaxed_candidate_response.json() == relaxed_candidate

        # -----------------------------------------------------------------
        # Fresh PostgreSQL reconstruction proves both immutable policy
        # snapshots and both candidate interpretations remain intact.
        # -----------------------------------------------------------------
        async with SessionLocal() as verify_db:
            policy_rows = list(
                (
                    await verify_db.execute(
                        select(ObjectiveLearningPolicyRevisionRecord)
                        .where(
                            ObjectiveLearningPolicyRevisionRecord.user_id == user_id,
                            ObjectiveLearningPolicyRevisionRecord.tenant_id
                            == tenant_id,
                        )
                        .order_by(
                            ObjectiveLearningPolicyRevisionRecord.policy_version.asc()
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert len(policy_rows) == 2
            assert [row.policy_version for row in policy_rows] == [1, 2]
            assert [row.profile_version for row in policy_rows] == [1, 1]
            assert [
                row.profile_json["qualification_policy"][
                    "minimum_effective_sample_size"
                ]
                for row in policy_rows
            ] == [5.0, 1.0]
            assert all(row.informational_only is True for row in policy_rows)
            assert all(row.authorizes_execution is False for row in policy_rows)

            candidate_rows = list(
                (
                    await verify_db.execute(
                        select(ObjectiveLearningCandidateRevisionRecord)
                        .where(
                            ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                            ObjectiveLearningCandidateRevisionRecord.candidate_id.in_(
                                (
                                    strict_candidate_id,
                                    relaxed_candidate_id,
                                )
                            ),
                        )
                        .order_by(
                            ObjectiveLearningCandidateRevisionRecord.policy_version.asc()
                        )
                    )
                )
                .scalars()
                .all()
            )

            assert len(candidate_rows) == 2
            assert [row.version for row in candidate_rows] == [1, 1]
            assert [row.policy_version for row in candidate_rows] == [1, 2]
            assert [row.profile_version for row in candidate_rows] == [1, 1]
            assert [row.validation_passed for row in candidate_rows] == [
                False,
                True,
            ]
            assert [row.status for row in candidate_rows] == [
                "blocked",
                "validated",
            ]
            assert [str(row.candidate_id) for row in candidate_rows] == [
                strict_candidate_id,
                relaxed_candidate_id,
            ]
            assert candidate_rows[0].candidate_json == strict_candidate
            assert candidate_rows[1].candidate_json == relaxed_candidate
            assert all(row.informational_only is True for row in candidate_rows)
            assert all(row.authorizes_execution is False for row in candidate_rows)

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
