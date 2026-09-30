from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


_HEALTH_MODES = {
    "off",
    "shadow",
    "enforce_unhealthy",
}


class CapabilityRuntimePolicyPatch(BaseModel):
    """
    Partial policy payload stored by one immutable revision.

    Fields omitted from a revision inherit from lower-precedence scopes.
    """

    model_config = ConfigDict(extra="forbid")

    health_enforcement_mode: str | None = None
    health_probe_lease_seconds: int | None = Field(
        default=None,
        ge=1,
        le=86_400,
    )
    health_probe_failure_cooldown_seconds: int | None = Field(
        default=None,
        ge=0,
        le=604_800,
    )

    performance_window_hours: int | None = Field(
        default=None,
        ge=1,
        le=8_760,
    )
    minimum_performance_attempts: int | None = Field(
        default=None,
        ge=1,
    )

    priority_weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    reliability_weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    latency_weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    allocation_enabled: bool | None = None
    competitive_allocation_margin: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    allocation_bucket_count: int | None = Field(
        default=None,
        ge=100,
        le=1_000_000,
    )
    maximum_allocation_candidates: int | None = Field(
        default=None,
        ge=2,
        le=100,
    )

    @model_validator(mode="after")
    def validate_patch(self):
        if (
            self.health_enforcement_mode is not None
            and self.health_enforcement_mode
            not in _HEALTH_MODES
        ):
            raise ValueError(
                "health_enforcement_mode must be one of: "
                "off, shadow, enforce_unhealthy"
            )

        supplied_weights = (
            self.priority_weight,
            self.reliability_weight,
            self.latency_weight,
        )

        if all(value is not None for value in supplied_weights):
            if abs(sum(supplied_weights) - 1.0) > 1e-9:
                raise ValueError(
                    "provider score weights must sum to 1.0"
                )

        return self

    def explicit_values(self) -> dict[str, Any]:
        return self.model_dump(
            exclude_none=True,
            mode="python",
        )


class CapabilityRuntimePolicy(BaseModel):
    """
    Fully resolved runtime policy after precedence merging.
    """

    model_config = ConfigDict(extra="forbid")

    health_enforcement_mode: str = "shadow"
    health_probe_lease_seconds: int = Field(
        default=60,
        ge=1,
        le=86_400,
    )
    health_probe_failure_cooldown_seconds: int = Field(
        default=300,
        ge=0,
        le=604_800,
    )

    performance_window_hours: int = Field(
        default=24,
        ge=1,
        le=8_760,
    )
    minimum_performance_attempts: int = Field(
        default=10,
        ge=1,
    )

    priority_weight: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
    )
    reliability_weight: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
    )
    latency_weight: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
    )

    allocation_enabled: bool = True
    competitive_allocation_margin: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
    )
    allocation_bucket_count: int = Field(
        default=10_000,
        ge=100,
        le=1_000_000,
    )
    maximum_allocation_candidates: int = Field(
        default=3,
        ge=2,
        le=100,
    )

    @model_validator(mode="after")
    def validate_policy(self):
        if self.health_enforcement_mode not in _HEALTH_MODES:
            raise ValueError(
                "health_enforcement_mode must be one of: "
                "off, shadow, enforce_unhealthy"
            )

        if (
            abs(
                self.priority_weight
                + self.reliability_weight
                + self.latency_weight
                - 1.0
            )
            > 1e-9
        ):
            raise ValueError(
                "provider score weights must sum to 1.0"
            )

        return self


class CapabilityRuntimePolicyScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    tenant_id: str | None = None
    capability_id: str | None = None
    provider_id: str | None = None
    provider_ref: str | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if (
            self.provider_ref is not None
            and self.provider_id is None
        ):
            raise ValueError(
                "provider_ref requires provider_id"
            )

        return self

    def scope_key(self) -> str:
        return "|".join(
            (
                str(self.user_id),
                self.tenant_id or "*",
                self.capability_id or "*",
                self.provider_id or "*",
                self.provider_ref or "*",
            )
        )


class CapabilityRuntimePolicyRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    policy_key: str
    scope_key: str

    user_id: UUID
    tenant_id: str | None = None
    capability_id: str | None = None
    provider_id: str | None = None
    provider_ref: str | None = None

    version: int = Field(ge=1)
    enabled: bool
    policy_payload: CapabilityRuntimePolicyPatch
    reason: str | None = None
    created_by_user_id: UUID | None = None
    created_at: Any


class CapabilityRuntimePolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool
    user_id: str | None = None
    tenant_id: str | None = None
    capability_id: str | None = None
    provider_id: str | None = None
    provider_ref: str | None = None

    effective_policy: CapabilityRuntimePolicy
    applied_revisions: tuple[
        CapabilityRuntimePolicyRevision,
        ...,
    ] = ()
    resolution_reason: str


@runtime_checkable
class CapabilityRuntimePolicyReader(Protocol):
    async def resolve_policy(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str | None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
    ) -> CapabilityRuntimePolicySnapshot:
        ...


class NullCapabilityRuntimePolicyReader:
    async def resolve_policy(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str | None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
    ) -> CapabilityRuntimePolicySnapshot:
        return CapabilityRuntimePolicySnapshot(
            found=False,
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            effective_policy=CapabilityRuntimePolicy(),
            resolution_reason="code_defaults",
        )


def policy_scope_precedence(
    revision: CapabilityRuntimePolicyRevision,
    *,
    tenant_id: str | None,
) -> tuple[int, int, int, int]:
    """
    Sort from broadest to most specific.

    User-wide revisions are applied before tenant-specific revisions. Inside
    either ownership level:
      default → capability → provider → capability+provider.
    """

    tenant_specific = int(
        tenant_id is not None
        and revision.tenant_id == tenant_id
    )
    capability_specific = int(
        revision.capability_id is not None
    )
    provider_specific = int(
        revision.provider_id is not None
    )
    provider_ref_specific = int(
        revision.provider_ref is not None
    )

    return (
        tenant_specific,
        capability_specific + provider_specific,
        provider_specific,
        provider_ref_specific,
    )


def merge_policy_revisions(
    *,
    revisions: list[CapabilityRuntimePolicyRevision],
    tenant_id: str | None,
) -> CapabilityRuntimePolicy:
    values = CapabilityRuntimePolicy().model_dump(
        mode="python"
    )

    for revision in sorted(
        revisions,
        key=lambda item: policy_scope_precedence(
            item,
            tenant_id=tenant_id,
        ),
    ):
        values.update(
            revision.policy_payload.explicit_values()
        )

    return CapabilityRuntimePolicy.model_validate(values)


__all__ = [
    "CapabilityRuntimePolicy",
    "CapabilityRuntimePolicyPatch",
    "CapabilityRuntimePolicyReader",
    "CapabilityRuntimePolicyRevision",
    "CapabilityRuntimePolicyScope",
    "CapabilityRuntimePolicySnapshot",
    "NullCapabilityRuntimePolicyReader",
    "merge_policy_revisions",
    "policy_scope_precedence",
]
