from __future__ import annotations

from typing import Any, Protocol


class ProviderInstallationVerifier(Protocol):
    """Verify one provider installation for a user."""

    async def verify(
        self,
        *,
        user_id: Any,
    ) -> dict[str, Any]:
        ...


class UnsupportedProviderVerificationError(ValueError):
    """Raised when no verifier is registered for a provider."""


class ProviderInstallationVerifierRegistry:
    """
    Maps provider ids to provider-owned installation verifiers.

    Runtime owns only this dispatch boundary. Provider-specific
    verification mechanics are registered by application composition.
    """

    def __init__(self) -> None:
        self._verifiers: dict[
            str,
            ProviderInstallationVerifier,
        ] = {}

    def register(
        self,
        provider_id: str,
        verifier: ProviderInstallationVerifier,
    ) -> None:
        normalized = self._normalize_provider_id(
            provider_id
        )

        if normalized in self._verifiers:
            raise ValueError(
                "Provider installation verifier "
                f"already registered: {normalized}"
            )

        self._verifiers[normalized] = verifier

    def has(
        self,
        provider_id: str,
    ) -> bool:
        normalized = self._normalize_provider_id(
            provider_id
        )
        return normalized in self._verifiers

    def get(
        self,
        provider_id: str,
    ) -> ProviderInstallationVerifier:
        normalized = self._normalize_provider_id(
            provider_id
        )

        verifier = self._verifiers.get(
            normalized
        )

        if verifier is None:
            raise UnsupportedProviderVerificationError(
                "Provider verification is not "
                f"supported for '{provider_id}'"
            )

        return verifier

    async def verify(
        self,
        provider_id: str,
        *,
        user_id: Any,
    ) -> dict[str, Any]:
        verifier = self.get(
            provider_id
        )

        return await verifier.verify(
            user_id=user_id
        )

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._verifiers)
        )

    @staticmethod
    def _normalize_provider_id(
        provider_id: str,
    ) -> str:
        normalized = str(
            provider_id or ""
        ).strip().lower()

        if not normalized:
            raise ValueError(
                "provider_id is required"
            )

        return normalized


__all__ = [
    "ProviderInstallationVerifier",
    "ProviderInstallationVerifierRegistry",
    "UnsupportedProviderVerificationError",
]
