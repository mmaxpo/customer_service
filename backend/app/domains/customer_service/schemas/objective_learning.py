from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import (
    ObjectiveLearningExperienceRecord,
    ObjectiveLearningPolicyRevisionRecord,
)

from app.runtime.objectives.learning import (
    ObjectiveLearningApprovedInsight,
    ObjectiveLearningCandidate,
    ObjectiveLearningProfile,
)


class ObjectiveLearningExperienceRead(BaseModel):
    """
    Immutable, informational objective-learning extraction snapshot.

    Returning this model does not activate Planner guidance, change
    ranking, alter workflow behavior, select a provider, or authorize
    execution.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    id: UUID
    user_id: UUID
    tenant_id: str | None

    resolution_record_id: UUID

    objective_namespace: str
    objective_type: str
    objective_ref: str
    objective_version: int = Field(ge=1)

    schema_ref: str
    profile_ref: str
    profile_version: int = Field(ge=1)
    extractor_ref: str
    extractor_version: int = Field(ge=1)

    outcome_ref: str
    evaluation_ref: str
    workflow_run_id: str | None

    dimension_keys: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    validity_scope: dict[str, Any]
    experience: dict[str, Any]

    informational_only: bool
    authorizes_execution: bool

    created_at: datetime

    @classmethod
    def from_record(
        cls,
        record: ObjectiveLearningExperienceRecord,
    ) -> "ObjectiveLearningExperienceRead":
        return cls(
            id=record.id,
            user_id=record.user_id,
            tenant_id=record.tenant_id,
            resolution_record_id=(record.resolution_record_id),
            objective_namespace=(record.objective_namespace),
            objective_type=record.objective_type,
            objective_ref=record.objective_ref,
            objective_version=record.objective_version,
            schema_ref=record.schema_ref,
            profile_ref=record.profile_ref,
            profile_version=record.profile_version,
            extractor_ref=record.extractor_ref,
            extractor_version=record.extractor_version,
            outcome_ref=record.outcome_ref,
            evaluation_ref=record.evaluation_ref,
            workflow_run_id=record.workflow_run_id,
            dimension_keys=tuple(record.dimension_keys_json or ()),
            evidence_refs=tuple(record.evidence_refs_json or ()),
            validity_scope=deepcopy(dict(record.validity_scope_json or {})),
            experience=deepcopy(dict(record.experience_json or {})),
            informational_only=bool(record.informational_only),
            authorizes_execution=bool(record.authorizes_execution),
            created_at=record.created_at,
        )


class ObjectiveLearningPolicyEnsureRequest(BaseModel):
    """
    Ensure the current server-owned customer-support learning policy.

    Policy identity, versions, thresholds, qualification behavior, and
    all safety controls remain server-owned.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    tenant_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )


class ObjectiveLearningPolicyRevisionRead(BaseModel):
    """
    Immutable durable policy definition.

    Reading or ensuring this record does not activate guidance, alter
    planning or ranking, select providers, modify workflow behavior, or
    authorize execution.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    id: UUID
    scope_key: str

    user_id: UUID
    tenant_id: str | None

    objective_namespace: str
    objective_type: str

    profile_ref: str
    profile_version: int = Field(ge=1)

    policy_ref: str
    policy_version: int = Field(ge=1)

    enabled: bool
    profile: ObjectiveLearningProfile

    reason: str | None
    created_by_user_id: UUID | None
    created_at: datetime

    informational_only: bool
    authorizes_execution: bool

    @classmethod
    def from_record(
        cls,
        record: ObjectiveLearningPolicyRevisionRecord,
    ) -> "ObjectiveLearningPolicyRevisionRead":
        return cls(
            id=record.id,
            scope_key=record.scope_key,
            user_id=record.user_id,
            tenant_id=record.tenant_id,
            objective_namespace=record.objective_namespace,
            objective_type=record.objective_type,
            profile_ref=record.profile_ref,
            profile_version=record.profile_version,
            policy_ref=record.policy_ref,
            policy_version=record.policy_version,
            enabled=bool(record.enabled),
            profile=ObjectiveLearningProfile.model_validate(record.profile_json),
            reason=record.reason,
            created_by_user_id=record.created_by_user_id,
            created_at=record.created_at,
            informational_only=bool(record.informational_only),
            authorizes_execution=bool(record.authorizes_execution),
        )


class ObjectiveLearningPolicyEnsureResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    revision: ObjectiveLearningPolicyRevisionRead
    created: bool


class ObjectiveLearningPolicyRevisionListResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    items: tuple[
        ObjectiveLearningPolicyRevisionRead,
        ...,
    ]
    count: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)


class ObjectiveLearningCandidateGenerateRequest(BaseModel):
    """
    Authenticated request for one explicit generation pass.

    Product profile identity, qualification thresholds, candidate
    policy, and all planning/execution safety controls remain
    server-owned and are not configurable through this request.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    tenant_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    window_hours: int = Field(
        default=720,
        ge=1,
        le=8760,
    )


class ObjectiveLearningExperienceListResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    items: tuple[
        ObjectiveLearningExperienceRead,
        ...,
    ]
    count: int = Field(ge=0)


__all__ = [
    "ObjectiveLearningApprovedInsightListResponse",
    "ObjectiveLearningCandidateGenerateRequest",
    "ObjectiveLearningCandidateListResponse",
    "ObjectiveLearningExperienceListResponse",
    "ObjectiveLearningExperienceRead",
    "ObjectiveLearningPolicyEnsureRequest",
    "ObjectiveLearningPolicyEnsureResponse",
    "ObjectiveLearningPolicyRevisionListResponse",
    "ObjectiveLearningPolicyRevisionRead",
]


class ObjectiveLearningCandidateListResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    items: tuple[
        ObjectiveLearningCandidate,
        ...,
    ]
    count: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)


class ObjectiveLearningApprovedInsightListResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    items: tuple[
        ObjectiveLearningApprovedInsight,
        ...,
    ]
    count: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)
