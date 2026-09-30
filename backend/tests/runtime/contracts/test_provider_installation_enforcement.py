from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    NullProviderInstallationReader,
    ProviderAuthenticationState,
    ProviderConfigurationState,
    ProviderInstallationSnapshot,
    ProviderVerificationState,
    build_default_executor_registry,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


def build_services(
    user_id,
    tenant_id,
):
    return SimpleNamespace(
        identity=SimpleNamespace(
            user_id=user_id,
            tenant_id=tenant_id,
        ),
        business=SimpleNamespace(
            shopify=None,
        ),
    )


class FakeInstallationReader:
    def __init__(
        self,
        snapshots,
    ):
        self.snapshots = snapshots
        self.calls = []

    async def get_provider_installation(
        self,
        *,
        user_id,
        tenant_id,
        provider_id,
    ):
        self.calls.append(
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "provider_id": provider_id,
            }
        )

        return self.snapshots[provider_id]


def available_snapshot(
    provider_id,
):
    return ProviderInstallationSnapshot(
        found=True,
        provider_id=provider_id,
        enabled=True,
        configuration_state=(
            ProviderConfigurationState.CONFIGURED
        ),
        authentication_state=(
            ProviderAuthenticationState.AUTHENTICATED
        ),
        verification_state=(
            ProviderVerificationState.VERIFIED
        ),
        integration_kind=provider_id,
        version=1,
    )


@pytest.mark.asyncio
async def test_uninstalled_provider_is_rejected_before_scoring():
    user_id = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    reader = FakeInstallationReader(
        {
            "shopify": ProviderInstallationSnapshot(
                found=False,
                provider_id="shopify",
                enabled=False,
                configuration_state=(
                    ProviderConfigurationState
                    .UNCONFIGURED
                ),
                authentication_state=(
                    ProviderAuthenticationState
                    .MISSING
                ),
                verification_state=(
                    ProviderVerificationState
                    .UNVERIFIED
                ),
            ),
            "mock": available_snapshot("mock"),
        }
    )

    resolver = CapabilityResolver(
        services=build_services(
            user_id,
            tenant_id,
        ),
        system=build_default_system(
            include_mock_provider=True
        ),
        executor_registry=(
            build_default_executor_registry()
        ),
        provider_installation_reader=reader,
    )

    resolution = await (
        resolver._resolve_provider_with_health(
            invocation=CapabilityInvocation(
                capability_id=(
                    "ecommerce.orders.get"
                ),
                inputs={"order_ref": "#1001"},
                user_id=user_id,
            ),
            denied_provider_ids=(),
        )
    )

    assert resolution.ok is True
    assert (
        resolution.selected_provider_id
        == "mock"
    )

    rejected = {
        item.provider_id: item.reason
        for item in resolution.rejected_providers
    }

    assert (
        rejected["shopify"]
        == "provider_not_installed"
    )

    enforcement = (
        resolution.metadata[
            "provider_installation_enforcement"
        ]
    )
    assert len(enforcement["candidates"]) == 2


@pytest.mark.asyncio
async def test_disabled_only_provider_fails_resolution():
    user_id = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    reader = FakeInstallationReader(
        {
            "shopify": ProviderInstallationSnapshot(
                found=True,
                provider_id="shopify",
                enabled=False,
                configuration_state=(
                    ProviderConfigurationState
                    .CONFIGURED
                ),
                authentication_state=(
                    ProviderAuthenticationState
                    .AUTHENTICATED
                ),
                verification_state=(
                    ProviderVerificationState
                    .VERIFIED
                ),
                integration_kind="shopify",
                version=2,
            ),
        }
    )

    resolver = CapabilityResolver(
        services=build_services(
            user_id,
            tenant_id,
        ),
        system=build_default_system(),
        executor_registry=(
            build_default_executor_registry()
        ),
        provider_installation_reader=reader,
    )

    resolution = await (
        resolver._resolve_provider_with_health(
            invocation=CapabilityInvocation(
                capability_id=(
                    "ecommerce.orders.get"
                ),
                inputs={"order_ref": "#1001"},
                user_id=user_id,
            ),
            denied_provider_ids=(),
        )
    )

    assert resolution.ok is False

    rejected = {
        item.provider_id: item.reason
        for item in resolution.rejected_providers
    }
    assert (
        rejected["shopify"]
        == "provider_disabled"
    )


@pytest.mark.asyncio
async def test_null_installation_reader_preserves_existing_selection():
    user_id = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    resolver = CapabilityResolver(
        services=build_services(
            user_id,
            tenant_id,
        ),
        system=build_default_system(),
        executor_registry=(
            build_default_executor_registry()
        ),
        provider_installation_reader=(
            NullProviderInstallationReader()
        ),
    )

    resolution = await (
        resolver._resolve_provider_with_health(
            invocation=CapabilityInvocation(
                capability_id=(
                    "ecommerce.orders.get"
                ),
                inputs={"order_ref": "#1001"},
                user_id=user_id,
            ),
            denied_provider_ids=(),
        )
    )

    assert resolution.ok is True
    assert (
        resolution.selected_provider_id
        == "shopify"
    )
    assert (
        resolution.rejected_providers
        == ()
    )


@pytest.mark.asyncio
async def test_installation_reader_failure_is_fail_open():
    class BrokenReader:
        async def get_provider_installation(
            self,
            **kwargs,
        ):
            raise RuntimeError(
                "installation store unavailable"
            )

    user_id = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    resolver = CapabilityResolver(
        services=build_services(
            user_id,
            tenant_id,
        ),
        system=build_default_system(),
        executor_registry=(
            build_default_executor_registry()
        ),
        provider_installation_reader=(
            BrokenReader()
        ),
    )

    resolution = await (
        resolver._resolve_provider_with_health(
            invocation=CapabilityInvocation(
                capability_id=(
                    "ecommerce.orders.get"
                ),
                inputs={"order_ref": "#1001"},
                user_id=user_id,
            ),
            denied_provider_ids=(),
        )
    )

    assert resolution.ok is True

    diagnostic = (
        resolution.metadata[
            "provider_installation_enforcement"
        ]["candidates"][0]
    )
    assert diagnostic["read_succeeded"] is False
    assert (
        "installation store unavailable"
        in diagnostic["reader_error"]
    )
