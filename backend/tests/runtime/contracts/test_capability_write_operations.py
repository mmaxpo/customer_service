from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.runtime.capabilities.execution.installation.operations import (
    CapabilityProviderInstallationOperations,
)
from app.runtime.capabilities.execution.policy.operations import (
    CapabilityRuntimePolicyOperations,
)


@pytest.mark.asyncio
async def test_runtime_policy_operation_commits_and_refreshes():
    row = object()

    repository = SimpleNamespace(append_revision=AsyncMock(return_value=row))

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await CapabilityRuntimePolicyOperations(
        db,
        repository=repository,
    ).append_revision(
        scope="scope",
        policy_payload="policy",
        enabled=True,
        reason="test",
        created_by_user_id="user",
    )

    assert result is row

    repository.append_revision.assert_awaited_once_with(
        scope="scope",
        policy_payload="policy",
        enabled=True,
        reason="test",
        created_by_user_id="user",
    )

    db.commit.assert_awaited_once_with()
    db.refresh.assert_awaited_once_with(row)
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_policy_operation_rolls_back_value_error():
    repository = SimpleNamespace(
        append_revision=AsyncMock(side_effect=ValueError("invalid"))
    )

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(
        ValueError,
        match="invalid",
    ):
        await CapabilityRuntimePolicyOperations(
            db,
            repository=repository,
        ).append_revision(
            scope="scope",
            policy_payload="policy",
            enabled=True,
            reason=None,
            created_by_user_id="user",
        )

    db.rollback.assert_awaited_once_with()
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_installation_enable_operation_preserves_atomic_event_and_commit():
    row = SimpleNamespace(enabled=True)

    repository = SimpleNamespace(set_enabled=AsyncMock(return_value=row))

    lifecycle = SimpleNamespace(enabled_changed=AsyncMock())

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await CapabilityProviderInstallationOperations(
        db,
        repository=repository,
    ).set_enabled(
        user_id="user",
        tenant_id=None,
        provider_id="shopify",
        enabled=True,
        lifecycle_events=lifecycle,
    )

    assert result is row

    repository.set_enabled.assert_awaited_once_with(
        user_id="user",
        tenant_id=None,
        provider_id="shopify",
        enabled=True,
    )

    lifecycle.enabled_changed.assert_awaited_once_with(
        user_id="user",
        installation=row,
    )

    db.commit.assert_awaited_once_with()
    db.refresh.assert_awaited_once_with(row)
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_installation_enable_missing_row_rolls_back_without_event():
    repository = SimpleNamespace(set_enabled=AsyncMock(return_value=None))

    lifecycle = SimpleNamespace(enabled_changed=AsyncMock())

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await CapabilityProviderInstallationOperations(
        db,
        repository=repository,
    ).set_enabled(
        user_id="user",
        tenant_id=None,
        provider_id="shopify",
        enabled=False,
        lifecycle_events=lifecycle,
    )

    assert result is None

    db.rollback.assert_awaited_once_with()
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()

    lifecycle.enabled_changed.assert_not_awaited()


@pytest.mark.asyncio
async def test_installation_reconcile_preserves_project_event_commit_refresh_sequence():
    row_a = object()
    row_b = object()

    projector = SimpleNamespace(
        reconcile_active_connections=AsyncMock(
            return_value=[
                row_a,
                row_b,
            ]
        )
    )

    lifecycle = SimpleNamespace(reconciled=AsyncMock())

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    operation = CapabilityProviderInstallationOperations(
        db,
        repository=SimpleNamespace(),
    )

    connections = [
        object(),
        object(),
        object(),
    ]

    result = await operation.reconcile(
        user_id="user",
        connections=connections,
        projector=projector,
        lifecycle_events=lifecycle,
    )

    assert result == [
        row_a,
        row_b,
    ]

    projector.reconcile_active_connections.assert_awaited_once_with(
        user_id="user",
        connections=connections,
    )

    lifecycle.reconciled.assert_awaited_once_with(
        user_id="user",
        installations=[
            row_a,
            row_b,
        ],
        discovered=3,
    )

    db.commit.assert_awaited_once_with()

    assert db.refresh.await_count == 2
    db.refresh.assert_any_await(row_a)
    db.refresh.assert_any_await(row_b)
