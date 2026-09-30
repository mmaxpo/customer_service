import pytest

from app.runtime.capabilities.execution.installation.verification import (
    ProviderInstallationVerifierRegistry,
    UnsupportedProviderVerificationError,
)


class FakeVerifier:
    def __init__(self) -> None:
        self.user_ids = []

    async def verify(
        self,
        *,
        user_id,
    ):
        self.user_ids.append(
            user_id
        )

        return {
            "ok": True,
            "message": "verified",
        }


@pytest.mark.asyncio
async def test_registry_dispatches_registered_provider():
    registry = ProviderInstallationVerifierRegistry()
    verifier = FakeVerifier()

    registry.register(
        "shopify",
        verifier,
    )

    result = await registry.verify(
        "shopify",
        user_id="user-1",
    )

    assert result == {
        "ok": True,
        "message": "verified",
    }
    assert verifier.user_ids == [
        "user-1"
    ]


@pytest.mark.asyncio
async def test_registry_normalizes_provider_id():
    registry = ProviderInstallationVerifierRegistry()
    verifier = FakeVerifier()

    registry.register(
        " Shopify ",
        verifier,
    )

    assert registry.has(
        "SHOPIFY"
    )

    result = await registry.verify(
        " shopify ",
        user_id="user-2",
    )

    assert result["ok"] is True
    assert registry.provider_ids() == (
        "shopify",
    )


def test_registry_rejects_duplicate_provider():
    registry = ProviderInstallationVerifierRegistry()

    registry.register(
        "shopify",
        FakeVerifier(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Provider installation verifier "
            "already registered"
        ),
    ):
        registry.register(
            "SHOPIFY",
            FakeVerifier(),
        )


@pytest.mark.asyncio
async def test_registry_rejects_unknown_provider():
    registry = ProviderInstallationVerifierRegistry()

    with pytest.raises(
        UnsupportedProviderVerificationError,
        match="not supported",
    ):
        await registry.verify(
            "unknown",
            user_id="user-3",
        )
