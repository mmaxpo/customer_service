from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


@pytest.mark.asyncio
async def test_runtime_policy_revision_and_effective_read():
    user_id = uuid4()
    tenant_id = f"tenant-policy-api-{uuid4()}"

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser(user_id)
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "tenant_id": tenant_id,
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "provider_id": "shopify",
                    "provider_ref": (
                        "shopify.get_order"
                    ),
                    "reason": (
                        "operator runtime policy"
                    ),
                    "policy_payload": {
                        "allocation_enabled": False,
                        "health_enforcement_mode": (
                            "enforce_unhealthy"
                        ),
                        "minimum_performance_attempts": 25,
                    },
                },
            )

            assert created.status_code == 201
            body = created.json()

            assert body["version"] == 1
            assert body["user_id"] == str(user_id)
            assert body["tenant_id"] == tenant_id
            assert body["created_by_user_id"] == (
                str(user_id)
            )
            assert (
                body["policy_payload"]
                ["allocation_enabled"]
                is False
            )

            effective = await client.get(
                "/capabilities/runtime-policy/effective",
                params={
                    "tenant_id": tenant_id,
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "provider_id": "shopify",
                    "provider_ref": (
                        "shopify.get_order"
                    ),
                },
            )

            assert effective.status_code == 200
            effective_body = effective.json()

            assert effective_body["found"] is True
            assert (
                effective_body["effective_policy"]
                ["allocation_enabled"]
                is False
            )
            assert (
                effective_body["effective_policy"]
                ["health_enforcement_mode"]
                == "enforce_unhealthy"
            )
            assert (
                effective_body["effective_policy"]
                ["minimum_performance_attempts"]
                == 25
            )
            assert len(
                effective_body["applied_revisions"]
            ) == 1
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_runtime_policy_history_is_user_scoped():
    first_user = uuid4()
    second_user = uuid4()
    tenant_id = f"tenant-policy-api-{uuid4()}"

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser(first_user)
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "tenant_id": tenant_id,
                    "policy_payload": {
                        "allocation_enabled": False,
                    },
                },
            )
            assert first.status_code == 201

            second = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "tenant_id": tenant_id,
                    "policy_payload": {
                        "allocation_enabled": True,
                    },
                },
            )
            assert second.status_code == 201
            assert second.json()["version"] == 2

            history = await client.get(
                "/capabilities/runtime-policy/revisions",
                params={
                    "tenant_id": tenant_id,
                },
            )

            assert history.status_code == 200
            assert len(history.json()["items"]) == 2
            assert [
                item["version"]
                for item in history.json()["items"]
            ] == [2, 1]

            app.dependency_overrides[
                get_current_user
            ] = lambda: FakeUser(second_user)

            hidden = await client.get(
                "/capabilities/runtime-policy/revisions",
                params={
                    "tenant_id": tenant_id,
                },
            )

            assert hidden.status_code == 200
            assert hidden.json()["items"] == []

            hidden_effective = await client.get(
                "/capabilities/runtime-policy/effective",
                params={
                    "tenant_id": tenant_id,
                },
            )

            assert hidden_effective.status_code == 200
            assert (
                hidden_effective.json()["found"]
                is False
            )
            assert (
                hidden_effective.json()
                ["resolution_reason"]
                == "code_defaults"
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_runtime_policy_payload_validation():
    user_id = uuid4()

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser(user_id)
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            invalid_mode = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "policy_payload": {
                        "health_enforcement_mode": (
                            "invalid"
                        ),
                    },
                },
            )

            assert invalid_mode.status_code == 422

            invalid_weights = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "policy_payload": {
                        "priority_weight": 0.5,
                        "reliability_weight": 0.5,
                        "latency_weight": 0.5,
                    },
                },
            )

            assert invalid_weights.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_disabled_latest_revision_suppresses_scope():
    user_id = uuid4()
    tenant_id = f"tenant-policy-disabled-{uuid4()}"

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser(user_id)
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            enabled = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "tenant_id": tenant_id,
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "policy_payload": {
                        "allocation_enabled": False,
                    },
                },
            )

            assert enabled.status_code == 201
            assert enabled.json()["version"] == 1

            disabled = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "tenant_id": tenant_id,
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "enabled": False,
                    "reason": "disable scoped override",
                    "policy_payload": {},
                },
            )

            assert disabled.status_code == 201
            assert disabled.json()["version"] == 2
            assert disabled.json()["enabled"] is False

            effective = await client.get(
                "/capabilities/runtime-policy/effective",
                params={
                    "tenant_id": tenant_id,
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                },
            )

            assert effective.status_code == 200
            body = effective.json()

            assert body["found"] is False
            assert (
                body["resolution_reason"]
                == "code_defaults"
            )
            assert (
                body["effective_policy"]
                ["allocation_enabled"]
                is True
            )

            history = await client.get(
                "/capabilities/runtime-policy/revisions",
                params={
                    "tenant_id": tenant_id,
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                },
            )

            assert history.status_code == 200
            assert [
                item["version"]
                for item in history.json()["items"]
            ] == [2, 1]
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_runtime_policy_rejects_provider_ref_without_provider():
    user_id = uuid4()

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser(user_id)
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "provider_ref": "shopify.get_order",
                    "policy_payload": {
                        "allocation_enabled": False,
                    },
                },
            )

            assert response.status_code == 422
            assert (
                "provider_ref requires provider_id"
                in response.json()["detail"]
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
