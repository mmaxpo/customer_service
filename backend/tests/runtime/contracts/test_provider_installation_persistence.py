from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.installation.models import (
    ProviderAuthenticationState,
    ProviderConfigurationState,
    ProviderInstallationScope,
    ProviderInstallationUpsert,
    ProviderVerificationState,
)
from app.runtime.capabilities.execution.installation.repository import (
    CapabilityProviderInstallationRepository,
    DatabaseProviderInstallationReader,
)


@pytest.mark.asyncio
async def test_provider_installation_round_trip():
    user_id = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    async with SessionLocal() as db:
        scope = ProviderInstallationScope(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id="shopify",
        )

        row = await (
            CapabilityProviderInstallationRepository(
                db
            )
            .upsert(
                scope=scope,
                installation=(
                    ProviderInstallationUpsert(
                        integration_kind="shopify",
                        integration_connection_id=(
                            str(uuid4())
                        ),
                        enabled=True,
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
                        metadata={
                            "shop_domain": (
                                "example.myshopify.com"
                            )
                        },
                    )
                ),
            )
        )

        await db.commit()

        assert row.version == 1

        snapshot = await (
            DatabaseProviderInstallationReader(
                db
            )
            .get_provider_installation(
                user_id=user_id,
                tenant_id=tenant_id,
                provider_id="shopify",
            )
        )

        assert snapshot.found is True
        assert snapshot.available is True
        assert (
            snapshot.rejection_reason(
                requires_auth=True
            )
            is None
        )
        assert (
            snapshot.metadata["shop_domain"]
            == "example.myshopify.com"
        )


@pytest.mark.asyncio
async def test_provider_installation_upsert_increments_version():
    user_id = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    async with SessionLocal() as db:
        repo = (
            CapabilityProviderInstallationRepository(
                db
            )
        )
        scope = ProviderInstallationScope(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id="shopify",
        )

        first = await repo.upsert(
            scope=scope,
            installation=ProviderInstallationUpsert(
                integration_kind="shopify",
            ),
        )
        await db.commit()

        assert first.version == 1

        second = await repo.upsert(
            scope=scope,
            installation=ProviderInstallationUpsert(
                integration_kind="shopify",
                enabled=False,
            ),
        )
        await db.commit()

        assert second.id == first.id
        assert second.version == 2
        assert second.enabled is False


@pytest.mark.asyncio
async def test_provider_installation_is_user_isolated():
    first_user = uuid4()
    second_user = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    async with SessionLocal() as db:
        await (
            CapabilityProviderInstallationRepository(
                db
            )
            .upsert(
                scope=ProviderInstallationScope(
                    user_id=first_user,
                    tenant_id=tenant_id,
                    provider_id="shopify",
                ),
                installation=(
                    ProviderInstallationUpsert(
                        integration_kind="shopify",
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
                    )
                ),
            )
        )
        await db.commit()

        hidden = await (
            DatabaseProviderInstallationReader(
                db
            )
            .get_provider_installation(
                user_id=second_user,
                tenant_id=tenant_id,
                provider_id="shopify",
            )
        )

        assert hidden.found is False
        assert hidden.available is False
        assert (
            hidden.rejection_reason(
                requires_auth=True
            )
            == "provider_not_installed"
        )


def test_verified_installation_requires_auth_and_configuration():
    with pytest.raises(
        ValueError,
        match="verified installation must be configured",
    ):
        ProviderInstallationUpsert(
            integration_kind="shopify",
            verification_state=(
                ProviderVerificationState.VERIFIED
            ),
        )

    with pytest.raises(
        ValueError,
        match="verified installation must be authenticated",
    ):
        ProviderInstallationUpsert(
            integration_kind="shopify",
            configuration_state=(
                ProviderConfigurationState.CONFIGURED
            ),
            verification_state=(
                ProviderVerificationState.VERIFIED
            ),
        )


def test_installation_rejection_reasons_are_deterministic():
    snapshot = (
        DatabaseProviderInstallationReader
    )

    del snapshot

    from app.runtime.capabilities.execution.installation.models import (
        ProviderInstallationSnapshot,
    )

    assert (
        ProviderInstallationSnapshot(
            found=True,
            provider_id="shopify",
            enabled=False,
        ).rejection_reason(
            requires_auth=True
        )
        == "provider_disabled"
    )

    assert (
        ProviderInstallationSnapshot(
            found=True,
            provider_id="shopify",
            enabled=True,
            configuration_state=(
                ProviderConfigurationState.CONFIGURED
            ),
            authentication_state=(
                ProviderAuthenticationState.EXPIRED
            ),
            verification_state=(
                ProviderVerificationState.UNVERIFIED
            ),
        ).rejection_reason(
            requires_auth=True
        )
        == "provider_authentication_expired"
    )


@pytest.mark.asyncio
async def test_tenant_read_falls_back_to_global_installation():
    user_id = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    async with SessionLocal() as db:
        await (
            CapabilityProviderInstallationRepository(
                db
            )
            .upsert(
                scope=ProviderInstallationScope(
                    user_id=user_id,
                    tenant_id=None,
                    provider_id="shopify",
                ),
                installation=(
                    ProviderInstallationUpsert(
                        integration_kind="shopify",
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
                    )
                ),
            )
        )
        await db.commit()

        snapshot = await (
            DatabaseProviderInstallationReader(
                db
            )
            .get_provider_installation(
                user_id=user_id,
                tenant_id=tenant_id,
                provider_id="shopify",
            )
        )

        assert snapshot.found is True
        assert snapshot.available is True
        assert snapshot.tenant_id is None


@pytest.mark.asyncio
async def test_tenant_installation_overrides_global_installation():
    user_id = uuid4()
    tenant_id = f"tenant-install-{uuid4()}"

    async with SessionLocal() as db:
        repo = (
            CapabilityProviderInstallationRepository(
                db
            )
        )

        await repo.upsert(
            scope=ProviderInstallationScope(
                user_id=user_id,
                tenant_id=None,
                provider_id="shopify",
            ),
            installation=ProviderInstallationUpsert(
                integration_kind="shopify",
                configuration_state=(
                    ProviderConfigurationState.CONFIGURED
                ),
                authentication_state=(
                    ProviderAuthenticationState
                    .AUTHENTICATED
                ),
                verification_state=(
                    ProviderVerificationState.VERIFIED
                ),
            ),
        )

        await repo.upsert(
            scope=ProviderInstallationScope(
                user_id=user_id,
                tenant_id=tenant_id,
                provider_id="shopify",
            ),
            installation=ProviderInstallationUpsert(
                integration_kind="shopify",
                enabled=False,
            ),
        )
        await db.commit()

        snapshot = await (
            DatabaseProviderInstallationReader(
                db
            )
            .get_provider_installation(
                user_id=user_id,
                tenant_id=tenant_id,
                provider_id="shopify",
            )
        )

        assert snapshot.found is True
        assert snapshot.tenant_id == tenant_id
        assert snapshot.enabled is False
        assert (
            snapshot.rejection_reason(
                requires_auth=True
            )
            == "provider_disabled"
        )
