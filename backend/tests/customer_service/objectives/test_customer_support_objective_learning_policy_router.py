from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.main import app
from app.models.models import (
    ObjectiveLearningPolicyRevisionRecord,
)
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self, user_id) -> None:
        self.id = user_id


@pytest.mark.asyncio
async def test_authenticated_policy_ensure_read_and_history():
    user_id = uuid4()
    tenant_id = f"tenant-policy-http-{uuid4()}"

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            missing = await client.get(
                "/customer-service/objective-learning/policies/current",
                params={"tenant_id": tenant_id},
            )
            assert missing.status_code == 404

            created_response = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert created_response.status_code == 201

            created_body = created_response.json()

            assert created_body["created"] is True

            revision = created_body["revision"]

            assert revision["user_id"] == str(user_id)
            assert revision["tenant_id"] == tenant_id
            assert revision["objective_namespace"] == ("customer_service.support")
            assert revision["objective_type"] == ("multi_operation")
            assert revision["profile_ref"] == (
                "customer_service.support.multi_operation"
            )
            assert revision["profile_version"] == 1
            assert revision["policy_ref"] == (
                "customer_service.support.objective_learning"
            )
            assert revision["policy_version"] == 1
            assert revision["enabled"] is True
            assert revision["informational_only"] is True
            assert revision["authorizes_execution"] is False

            profile = revision["profile"]
            qualification = profile["qualification_policy"]

            assert profile["profile_version"] == 1
            assert qualification["policy_version"] == 1
            assert qualification["minimum_confidence"] == 0.9
            assert qualification["minimum_effective_sample_size"] == 1.0
            assert qualification["informational_only"] is True
            assert qualification["affects_ranking"] is False
            assert qualification["affects_capability_selection"] is False
            assert qualification["affects_business_plan"] is False
            assert qualification["selects_provider"] is False
            assert qualification["authorizes_execution"] is False
            assert qualification["bypasses_approval"] is False
            assert qualification["bypasses_verification"] is False

            revision_id = revision["id"]

            repeated_response = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert repeated_response.status_code == 201
            assert repeated_response.json()["created"] is False
            assert repeated_response.json()["revision"]["id"] == revision_id

            current = await client.get(
                "/customer-service/objective-learning/policies/current",
                params={"tenant_id": tenant_id},
            )

            assert current.status_code == 200
            assert current.json() == revision

            exact = await client.get(
                "/customer-service/objective-learning/policies/1",
                params={"tenant_id": tenant_id},
            )

            assert exact.status_code == 200
            assert exact.json() == revision

            missing_version = await client.get(
                "/customer-service/objective-learning/policies/2",
                params={"tenant_id": tenant_id},
            )
            assert missing_version.status_code == 404

            history = await client.get(
                "/customer-service/objective-learning/policies",
                params={"tenant_id": tenant_id},
            )

            assert history.status_code == 200
            assert history.json() == {
                "items": [revision],
                "count": 1,
                "limit": 100,
                "offset": 0,
            }

            paged = await client.get(
                "/customer-service/objective-learning/policies",
                params={
                    "tenant_id": tenant_id,
                    "limit": 1,
                    "offset": 1,
                },
            )

            assert paged.status_code == 200
            assert paged.json() == {
                "items": [],
                "count": 0,
                "limit": 1,
                "offset": 1,
            }

            forbidden_override = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={
                    "tenant_id": tenant_id,
                    "policy_version": 999,
                    "minimum_confidence": 0.01,
                },
            )

            assert forbidden_override.status_code == 422

        async with SessionLocal() as verify_db:
            rows = list(
                (
                    await verify_db.execute(
                        select(ObjectiveLearningPolicyRevisionRecord).where(
                            ObjectiveLearningPolicyRevisionRecord.user_id == user_id,
                            ObjectiveLearningPolicyRevisionRecord.tenant_id
                            == tenant_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert len(rows) == 1
        assert str(rows[0].id) == revision_id
        assert rows[0].policy_version == 1

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_policy_http_reads_are_user_scoped():
    owner_id = uuid4()
    other_user_id = uuid4()
    tenant_id = f"tenant-policy-http-{uuid4()}"

    app.dependency_overrides[get_current_user] = lambda: FakeUser(owner_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert created.status_code == 201

            revision_id = created.json()["revision"]["id"]

            app.dependency_overrides[get_current_user] = lambda: FakeUser(other_user_id)

            hidden_current = await client.get(
                "/customer-service/objective-learning/policies/current",
                params={"tenant_id": tenant_id},
            )
            assert hidden_current.status_code == 404

            hidden_exact = await client.get(
                "/customer-service/objective-learning/policies/1",
                params={"tenant_id": tenant_id},
            )
            assert hidden_exact.status_code == 404

            hidden_history = await client.get(
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

            other_user_created = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert other_user_created.status_code == 201
            assert other_user_created.json()["created"] is True
            assert other_user_created.json()["revision"]["id"] != revision_id

        async with SessionLocal() as verify_db:
            count = await verify_db.scalar(
                select(func.count())
                .select_from(ObjectiveLearningPolicyRevisionRecord)
                .where(ObjectiveLearningPolicyRevisionRecord.tenant_id == tenant_id)
            )

        assert count == 2

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_policy_ensure_reports_durable_definition_drift():
    user_id = uuid4()
    tenant_id = f"tenant-policy-http-{uuid4()}"

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert created.status_code == 201
            revision_id = created.json()["revision"]["id"]

        async with SessionLocal() as mutation_db:
            record = await mutation_db.get(
                ObjectiveLearningPolicyRevisionRecord,
                revision_id,
            )

            assert record is not None

            drifted = dict(record.profile_json)
            qualification = dict(drifted["qualification_policy"])
            qualification["minimum_confidence"] = 0.2
            drifted["qualification_policy"] = qualification
            record.profile_json = drifted

            await mutation_db.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conflict = await client.post(
                "/customer-service/objective-learning/policies/current",
                json={"tenant_id": tenant_id},
            )

            assert conflict.status_code == 409
            assert (
                "does not match the server-owned definition"
                in conflict.json()["detail"]
            )

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


def test_policy_static_routes_precede_version_route():
    policy_routes = [
        route.path
        for route in app.routes
        if route.path.startswith("/customer-service/objective-learning/policies")
    ]

    current_index = policy_routes.index(
        "/customer-service/objective-learning/policies/current"
    )
    version_index = policy_routes.index(
        "/customer-service/objective-learning/policies/{policy_version}"
    )

    assert current_index < version_index
