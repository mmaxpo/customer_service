from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderConfigurationState(StrEnum):
    UNCONFIGURED = "unconfigured"
    CONFIGURED = "configured"
    INVALID = "invalid"


class ProviderAuthenticationState(StrEnum):
    MISSING = "missing"
    AUTHENTICATED = "authenticated"
    INVALID = "invalid"
    EXPIRED = "expired"


class ProviderVerificationState(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FAILED = "failed"


class ProviderInstallationScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    tenant_id: str | None = None
    provider_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_scope(self):
        self.provider_id = self.provider_id.strip()

        if self.tenant_id is not None:
            normalized_tenant = self.tenant_id.strip()
            self.tenant_id = normalized_tenant or None

        return self

    def scope_key(self) -> str:
        return "|".join(
            (
                str(self.user_id),
                self.tenant_id or "",
                self.provider_id,
            )
        )


class ProviderInstallationUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    integration_kind: str = Field(min_length=1)
    integration_connection_id: str | None = None

    enabled: bool = True

    configuration_state: ProviderConfigurationState = (
        ProviderConfigurationState.UNCONFIGURED
    )
    authentication_state: ProviderAuthenticationState = (
        ProviderAuthenticationState.MISSING
    )
    verification_state: ProviderVerificationState = (
        ProviderVerificationState.UNVERIFIED
    )

    failure_code: str | None = None
    failure_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_projection(self):
        self.integration_kind = (
            self.integration_kind.strip()
        )

        if self.integration_connection_id is not None:
            normalized_connection_id = (
                self.integration_connection_id.strip()
            )
            self.integration_connection_id = (
                normalized_connection_id or None
            )

        if (
            self.verification_state
            == ProviderVerificationState.VERIFIED
            and self.configuration_state
            != ProviderConfigurationState.CONFIGURED
        ):
            raise ValueError(
                "verified installation must be configured"
            )

        if (
            self.verification_state
            == ProviderVerificationState.VERIFIED
            and self.authentication_state
            != ProviderAuthenticationState.AUTHENTICATED
        ):
            raise ValueError(
                "verified installation must be authenticated"
            )

        return self


class ProviderInstallationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool

    user_id: str | None = None
    tenant_id: str | None = None
    provider_id: str

    enabled: bool = True
    configuration_state: ProviderConfigurationState = (
        ProviderConfigurationState.CONFIGURED
    )
    authentication_state: ProviderAuthenticationState = (
        ProviderAuthenticationState.AUTHENTICATED
    )
    verification_state: ProviderVerificationState = (
        ProviderVerificationState.VERIFIED
    )

    integration_kind: str | None = None
    integration_connection_id: str | None = None

    failure_code: str | None = None
    failure_message: str | None = None
    version: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def available(self) -> bool:
        return bool(
            self.enabled
            and self.configuration_state
            == ProviderConfigurationState.CONFIGURED
            and self.authentication_state
            == ProviderAuthenticationState.AUTHENTICATED
            and self.verification_state
            == ProviderVerificationState.VERIFIED
        )

    def rejection_reason(
        self,
        *,
        requires_auth: bool,
    ) -> str | None:
        # Null/fail-open readers return a synthetic available snapshot even
        # though no durable record was found. A durable reader returns an
        # unavailable snapshot when the provider is not installed.
        if not self.found:
            if self.available:
                return None
            return "provider_not_installed"

        if not self.enabled:
            return "provider_disabled"

        if (
            self.configuration_state
            == ProviderConfigurationState.UNCONFIGURED
        ):
            return "provider_not_configured"

        if (
            self.configuration_state
            == ProviderConfigurationState.INVALID
        ):
            return "provider_configuration_invalid"

        if requires_auth:
            if (
                self.authentication_state
                == ProviderAuthenticationState.MISSING
            ):
                return "provider_authentication_missing"

            if (
                self.authentication_state
                == ProviderAuthenticationState.EXPIRED
            ):
                return "provider_authentication_expired"

            if (
                self.authentication_state
                == ProviderAuthenticationState.INVALID
            ):
                return "provider_authentication_invalid"

        if (
            self.verification_state
            == ProviderVerificationState.UNVERIFIED
        ):
            return "provider_configuration_unverified"

        if (
            self.verification_state
            == ProviderVerificationState.FAILED
        ):
            return "provider_verification_failed"

        return None


class ProviderInstallationReader(Protocol):
    async def get_provider_installation(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        provider_id: str,
    ) -> ProviderInstallationSnapshot:
        ...


class NullProviderInstallationReader(ProviderInstallationReader):
    """
    Compatibility reader for runtimes without durable installation storage.

    Missing infrastructure remains fail-open so existing tests and non-database
    runtimes preserve their current provider-selection behavior.
    """

    async def get_provider_installation(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        provider_id: str,
    ) -> ProviderInstallationSnapshot:
        return ProviderInstallationSnapshot(
            found=False,
            user_id=(
                str(user_id)
                if user_id is not None
                else None
            ),
            tenant_id=tenant_id,
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
            metadata={
                "reason": (
                    "provider_installation_reader_not_configured"
                )
            },
        )


__all__ = [
    "NullProviderInstallationReader",
    "ProviderAuthenticationState",
    "ProviderConfigurationState",
    "ProviderInstallationReader",
    "ProviderInstallationScope",
    "ProviderInstallationSnapshot",
    "ProviderInstallationUpsert",
    "ProviderVerificationState",
]
