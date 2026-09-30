from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.runtime.objectives.learning.contracts import (
    ObjectiveLearningProfile,
)


class ObjectiveLearningPolicyScope(BaseModel):
    """
    Exact authenticated ownership and objective-family boundary for one
    append-only objective-learning policy lineage.

    Product-specific policy semantics remain inside ObjectiveLearningProfile.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    user_id: UUID
    tenant_id: str | None = None

    objective_namespace: str = Field(min_length=1)
    objective_type: str = Field(min_length=1)

    profile_ref: str = Field(min_length=1)
    policy_ref: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_scope(self) -> "ObjectiveLearningPolicyScope":
        for field_name in (
            "objective_namespace",
            "objective_type",
            "profile_ref",
            "policy_ref",
        ):
            normalized = str(getattr(self, field_name)).strip().lower()

            if not normalized:
                raise ValueError(f"objective-learning policy {field_name} is required")

            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        if self.tenant_id is not None:
            normalized_tenant = self.tenant_id.strip()

            object.__setattr__(
                self,
                "tenant_id",
                normalized_tenant or None,
            )

        return self

    def scope_key(self) -> str:
        return "|".join(
            (
                str(self.user_id),
                self.tenant_id or "*",
                self.objective_namespace,
                self.objective_type,
                self.profile_ref,
                self.policy_ref,
            )
        )

    def validate_profile(
        self,
        profile: ObjectiveLearningProfile,
    ) -> None:
        policy = profile.qualification_policy

        expected = (
            self.objective_namespace,
            self.objective_type,
            self.profile_ref,
            self.policy_ref,
        )
        actual = (
            profile.objective_namespace,
            profile.objective_type,
            profile.profile_ref,
            policy.policy_ref,
        )

        if actual != expected:
            raise ValueError(
                "objective-learning profile does not match durable policy scope"
            )


class ObjectiveLearningPolicyRevision(BaseModel):
    """
    Immutable durable snapshot of one complete objective-learning profile
    and qualification policy version.

    The revision remains informational and advisory only. Persistence does
    not activate planning, ranking, provider selection, workflow behavior,
    runtime policy, or execution.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    id: UUID
    scope_key: str = Field(min_length=1)

    user_id: UUID
    tenant_id: str | None = None

    objective_namespace: str = Field(min_length=1)
    objective_type: str = Field(min_length=1)

    profile_ref: str = Field(min_length=1)
    profile_version: int = Field(ge=1)

    policy_ref: str = Field(min_length=1)
    policy_version: int = Field(ge=1)

    enabled: bool = True
    profile: ObjectiveLearningProfile

    reason: str | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime

    informational_only: bool = True
    authorizes_execution: bool = False

    @model_validator(mode="after")
    def validate_revision(
        self,
    ) -> "ObjectiveLearningPolicyRevision":
        scope = ObjectiveLearningPolicyScope(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            objective_namespace=self.objective_namespace,
            objective_type=self.objective_type,
            profile_ref=self.profile_ref,
            policy_ref=self.policy_ref,
        )

        if self.scope_key != scope.scope_key():
            raise ValueError(
                "objective-learning policy scope_key does not match revision identity"
            )

        scope.validate_profile(self.profile)

        if self.profile.profile_version != self.profile_version:
            raise ValueError(
                "objective-learning profile_version does not match "
                "the persisted profile"
            )

        if self.profile.qualification_policy.policy_version != self.policy_version:
            raise ValueError(
                "objective-learning policy_version does not match the persisted profile"
            )

        if not self.informational_only:
            raise ValueError(
                "objective-learning policy revisions must remain informational only"
            )

        if self.authorizes_execution:
            raise ValueError(
                "objective-learning policy revisions cannot authorize execution"
            )

        return self


__all__ = [
    "ObjectiveLearningPolicyRevision",
    "ObjectiveLearningPolicyScope",
]
