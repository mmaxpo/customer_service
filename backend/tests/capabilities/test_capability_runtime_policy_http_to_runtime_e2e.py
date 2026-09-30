from __future__ import annotations

import runpy
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.api.auth import get_current_user
from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    DatabaseCapabilityRuntimePolicyReader,
    DeterministicProviderTrafficAllocator,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


CAPABILITY_ID = "ecommerce.orders.get"


class FakeUser:
    def __init__(self, user_id) -> None:
        self.id = user_id


def _consumption_helpers() -> dict[str, Any]:
    """
    Reuse the proven deterministic scorer and executor fixtures
    from the capability runtime-policy consumption contracts.

    The policy reader is deliberately not reused: this E2E uses
    the real PostgreSQL-backed reader after creating revisions
    through the actual FastAPI endpoint.
    """

    return runpy.run_path(
        "tests/runtime/contracts/test_capability_runtime_policy_consumption.py"
    )


def _runtime_services(
    *,
    user_id,
    tenant_id: str,
):
    return SimpleNamespace(
        identity=SimpleNamespace(
            user_id=str(user_id),
            tenant_id=tenant_id,
        ),
        business=SimpleNamespace(),
        db=None,
    )


async def _resolve_order_capability(
    *,
    user_id,
    tenant_id: str,
):
    helpers = _consumption_helpers()

    competitive_scorer = helpers["CompetitiveScorer"]
    build_executors = helpers["build_executors"]

    executor_calls: list[str] = []

    async with SessionLocal() as runtime_db:
        resolver = CapabilityResolver(
            services=_runtime_services(
                user_id=user_id,
                tenant_id=tenant_id,
            ),
            system=build_default_system(
                include_mock_provider=True,
            ),
            executor_registry=build_executors(executor_calls),
            provider_performance_scorer=(competitive_scorer()),
            provider_traffic_allocator=(DeterministicProviderTrafficAllocator()),
            capability_runtime_policy_reader=(
                DatabaseCapabilityRuntimePolicyReader(runtime_db)
            ),
        )

        result = await resolver.resolve(
            CapabilityInvocation(
                capability_id=CAPABILITY_ID,
                correlation_id=("http-a-stable-allocation-request"),
                inputs={
                    "order_ref": "#HTTP-A-1001",
                },
            )
        )

    return result, executor_calls


def _runtime_policy_metadata(result):
    resolution = result.metadata["resolution"]

    return (
        resolution["metadata"]["capability_runtime_policy"],
        resolution["metadata"]["provider_allocation"],
    )


@pytest.mark.asyncio
async def test_http_policy_revision_changes_real_runtime_behavior():
    """
    Turn the capability steering wheel through HTTP and verify
    that a fresh runtime resolver consumes the committed policy.

    Revision 1 disables allocation. Revision 2 enables it again.
    The capability input and runtime fixtures remain unchanged.
    """

    user_id = uuid4()
    second_user_id = uuid4()
    tenant_id = f"tenant-http-runtime-{uuid4()}"

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # -------------------------------------------------
            # Revision 1: turn competitive allocation OFF.
            # -------------------------------------------------
            disabled = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "tenant_id": tenant_id,
                    "capability_id": CAPABILITY_ID,
                    "reason": ("HTTP-A disable provider allocation"),
                    "policy_payload": {
                        "allocation_enabled": False,
                    },
                },
            )

            assert disabled.status_code == 201
            disabled_body = disabled.json()

            assert disabled_body["version"] == 1
            assert disabled_body["enabled"] is True
            assert disabled_body["user_id"] == str(user_id)
            assert disabled_body["tenant_id"] == tenant_id
            assert disabled_body["capability_id"] == CAPABILITY_ID
            assert disabled_body["policy_payload"]["allocation_enabled"] is False

            effective_disabled = await client.get(
                "/capabilities/runtime-policy/effective",
                params={
                    "tenant_id": tenant_id,
                    "capability_id": CAPABILITY_ID,
                },
            )

            assert effective_disabled.status_code == 200
            effective_disabled_body = effective_disabled.json()

            assert effective_disabled_body["found"] is True
            assert (
                effective_disabled_body["resolution_reason"] == "durable_policy_merged"
            )
            assert (
                effective_disabled_body["effective_policy"]["allocation_enabled"]
                is False
            )
            assert [
                revision["version"]
                for revision in (effective_disabled_body["applied_revisions"])
            ] == [1]

        disabled_result, disabled_calls = await _resolve_order_capability(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert disabled_result.ok is True
        assert disabled_calls == ["shopify"]

        (
            disabled_policy,
            disabled_allocation,
        ) = _runtime_policy_metadata(disabled_result)

        assert disabled_policy["found"] is True
        assert disabled_policy["resolution_reason"] == "durable_policy_merged"
        assert disabled_policy["effective_policy"]["allocation_enabled"] is False
        assert disabled_allocation["allocation_applied"] is False
        assert disabled_allocation["reason"] == "disabled_by_runtime_policy"

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # -------------------------------------------------
            # Revision 2: turn the same steering control ON.
            # -------------------------------------------------
            enabled = await client.post(
                "/capabilities/runtime-policy/revisions",
                json={
                    "tenant_id": tenant_id,
                    "capability_id": CAPABILITY_ID,
                    "reason": ("HTTP-A enable provider allocation"),
                    "policy_payload": {
                        "allocation_enabled": True,
                    },
                },
            )

            assert enabled.status_code == 201
            enabled_body = enabled.json()

            assert enabled_body["version"] == 2
            assert enabled_body["policy_payload"]["allocation_enabled"] is True

            effective_enabled = await client.get(
                "/capabilities/runtime-policy/effective",
                params={
                    "tenant_id": tenant_id,
                    "capability_id": CAPABILITY_ID,
                },
            )

            assert effective_enabled.status_code == 200
            effective_enabled_body = effective_enabled.json()

            assert (
                effective_enabled_body["effective_policy"]["allocation_enabled"] is True
            )

            # Only the latest revision for an exact scope is
            # applied to effective-policy resolution.
            assert [
                revision["version"]
                for revision in (effective_enabled_body["applied_revisions"])
            ] == [2]

            history = await client.get(
                "/capabilities/runtime-policy/revisions",
                params={
                    "tenant_id": tenant_id,
                    "capability_id": CAPABILITY_ID,
                },
            )

            assert history.status_code == 200
            assert [item["version"] for item in history.json()["items"]] == [2, 1]

        enabled_result, enabled_calls = await _resolve_order_capability(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert enabled_result.ok is True
        assert len(enabled_calls) == 1
        assert enabled_calls[0] in {
            "shopify",
            "mock",
        }

        (
            enabled_policy,
            enabled_allocation,
        ) = _runtime_policy_metadata(enabled_result)

        assert enabled_policy["found"] is True
        assert enabled_policy["effective_policy"]["allocation_enabled"] is True
        assert enabled_allocation["allocation_applied"] is True
        assert enabled_allocation["reason"] != "disabled_by_runtime_policy"

        # Same capability and evidence, different durable
        # steering configuration, different runtime behavior.
        assert (
            disabled_allocation["allocation_applied"]
            is not enabled_allocation["allocation_applied"]
        )

        # -----------------------------------------------------
        # Authentication isolation: another user sees defaults
        # and cannot consume the first user's steering policy.
        # -----------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: FakeUser(second_user_id)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            hidden_effective = await client.get(
                "/capabilities/runtime-policy/effective",
                params={
                    "tenant_id": tenant_id,
                    "capability_id": CAPABILITY_ID,
                },
            )

            assert hidden_effective.status_code == 200
            hidden_body = hidden_effective.json()

            assert hidden_body["found"] is False
            assert hidden_body["resolution_reason"] == "code_defaults"
            assert hidden_body["applied_revisions"] == []

            hidden_history = await client.get(
                "/capabilities/runtime-policy/revisions",
                params={
                    "tenant_id": tenant_id,
                    "capability_id": CAPABILITY_ID,
                },
            )

            assert hidden_history.status_code == 200
            assert hidden_history.json()["items"] == []

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
