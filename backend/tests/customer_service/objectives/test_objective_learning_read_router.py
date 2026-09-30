from __future__ import annotations

import runpy
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_recording import (
    CustomerSupportObjectiveLearningRecordingService,
)
from app.main import app
from app.api.auth import get_current_user
from app.runtime.objectives.learning import (
    ObjectiveLearningExperienceRepository,
)


class FakeUser:
    def __init__(self, user_id) -> None:
        self.id = user_id


def _existing_seed_helpers():
    """
    Reuse the already-proven customer-support objective-learning
    resolution and source construction helpers.

    The HTTP test adds no new extraction fixture or product
    interpretation.
    """

    return runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_"
        "retry_recovery_e2e.py"
    )


@pytest.mark.asyncio
async def test_authenticated_objective_learning_reads():
    helpers = _existing_seed_helpers()

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
            resolution_record_id=(resolution_record_id),
        )

        repository = ObjectiveLearningExperienceRepository(setup_db)

        write = await CustomerSupportObjectiveLearningRecordingService(
            setup_db,
            source_loader=static_source_loader(source),
            repository=repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=(resolution_record_id),
        )

        experience_record = write.record

        experience_id = experience_record.id

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            detail = await client.get(
                f"/customer-service/objective-learning/experiences/{experience_id}"
            )

            assert detail.status_code == 200

            detail_body = detail.json()

            assert detail_body["id"] == str(experience_id)
            assert detail_body["user_id"] == str(user_id)
            assert detail_body["resolution_record_id"] == str(resolution_record_id)
            assert (
                detail_body["objective_namespace"]
                == experience_record.objective_namespace
            )
            assert detail_body["objective_type"] == experience_record.objective_type
            assert detail_body["informational_only"] is True
            assert detail_body["authorizes_execution"] is False
            assert detail_body["experience"]
            assert detail_body["validity_scope"]
            assert detail_body["evidence_refs"]

            resolution_history = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"resolutions/{resolution_record_id}/"
                "experiences"
            )

            assert resolution_history.status_code == 200

            history_body = resolution_history.json()

            assert history_body["count"] == 1
            assert [item["id"] for item in history_body["items"]] == [
                str(experience_id)
            ]

            summaries = await client.get(
                "/customer-service/objective-learning/summaries",
                params={
                    "tenant_id": (experience_record.tenant_id),
                    "objective_namespace": (experience_record.objective_namespace),
                    "objective_type": (experience_record.objective_type),
                    "objective_version": (experience_record.objective_version),
                    "schema_ref": (experience_record.schema_ref),
                    "profile_ref": (experience_record.profile_ref),
                    "profile_version": (experience_record.profile_version),
                    "extractor_ref": (experience_record.extractor_ref),
                    "extractor_version": (experience_record.extractor_version),
                },
            )

            assert summaries.status_code == 200

            summary_body = summaries.json()

            assert len(summary_body) == 1
            assert summary_body[0]["total_experiences"] == 1
            assert summary_body[0]["informational_only"] is True
            assert summary_body[0]["authorizes_execution"] is False

            # The default aggregation policy requires
            # more than one effective experience.
            assert summary_body[0]["evidence_sufficient"] is False

            invalid_window = await client.get(
                "/customer-service/objective-learning/summaries",
                params={"window_hours": 0},
            )

            assert invalid_window.status_code == 422

        # -------------------------------------------------
        # Authenticated isolation.
        # -------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: FakeUser(other_user_id)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            hidden_detail = await client.get(
                f"/customer-service/objective-learning/experiences/{experience_id}"
            )

            assert hidden_detail.status_code == 404

            hidden_history = await client.get(
                "/customer-service/"
                "objective-learning/"
                f"resolutions/{resolution_record_id}/"
                "experiences"
            )

            assert hidden_history.status_code == 200
            assert hidden_history.json() == {
                "items": [],
                "count": 0,
            }

            hidden_summaries = await client.get(
                "/customer-service/objective-learning/summaries",
                params={
                    "tenant_id": (experience_record.tenant_id),
                    "objective_namespace": (experience_record.objective_namespace),
                    "objective_type": (experience_record.objective_type),
                },
            )

            assert hidden_summaries.status_code == 200
            assert hidden_summaries.json() == []

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
