from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.objectives.learning.aggregation import (
    ObjectiveLearningAggregation,
)
from app.runtime.objectives.learning.lifecycle import (
    ObjectiveLearningApprovalStatus,
    ObjectiveLearningCandidate,
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidateStatus,
)
from app.runtime.objectives.learning.lifecycle_repository import (
    ObjectiveLearningCandidateRepository,
)


class ObjectiveLearningReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class ObjectiveLearningCandidateGenerationItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    candidate: ObjectiveLearningCandidate
    created: bool


class ObjectiveLearningCandidateGenerationResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    candidate: ObjectiveLearningCandidate
    created: bool

    @property
    def created_candidates(self) -> int:
        return int(self.created)

    @property
    def existing_candidates(self) -> int:
        return int(not self.created)

    @property
    def item(self) -> ObjectiveLearningCandidateGenerationItem:
        return ObjectiveLearningCandidateGenerationItem(
            candidate=self.candidate,
            created=self.created,
        )


class ObjectiveLearningCandidateReviewRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    decision: ObjectiveLearningReviewDecision
    reason: str = Field(min_length=1)
    reviewed_at: datetime | None = None

    @field_validator("reason")
    @classmethod
    def normalize_reason(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("objective learning review reason must not be empty")

        return normalized


class ObjectiveLearningLifecycleOperations:
    """
    User-scoped lifecycle composition for objective-learning candidates.

    This service:
      - proposes one deterministic candidate from one aggregation;
      - returns an existing deterministic candidate identity idempotently;
      - exposes authenticated latest/history reads;
      - applies pure approve/reject lifecycle transitions;
      - persists transitions as append-only revisions.

    It does not publish events, enqueue jobs, activate guidance, rank
    candidates, alter planning, select capabilities/providers, change
    workflow behavior, bypass approval/verification, or authorize execution.
    """

    def __init__(
        self,
        *,
        db: AsyncSession,
        repository: (ObjectiveLearningCandidateRepository | None) = None,
        factory: ObjectiveLearningCandidateFactory | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or ObjectiveLearningCandidateRepository(db)
        self.factory = factory or ObjectiveLearningCandidateFactory()

    async def propose(
        self,
        *,
        user_id: UUID,
        aggregation: ObjectiveLearningAggregation,
        proposed_at: datetime | None = None,
    ) -> ObjectiveLearningCandidateGenerationResult:
        candidate = self.factory.propose(
            aggregation=aggregation,
            proposed_at=proposed_at,
        )

        existing_row = await self.repository.get_latest_for_user(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )

        if existing_row is not None:
            existing = self.repository.deserialize(existing_row)

            return ObjectiveLearningCandidateGenerationResult(
                candidate=existing,
                created=False,
            )

        row = await self.repository.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        return ObjectiveLearningCandidateGenerationResult(
            candidate=self.repository.deserialize(row),
            created=True,
        )

    async def list_latest(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        objective_version: int | None = None,
        schema_ref: str | None = None,
        profile_ref: str | None = None,
        profile_version: int | None = None,
        extractor_ref: str | None = None,
        extractor_version: int | None = None,
        status: str | None = None,
        approval_status: str | None = None,
        validation_passed: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ObjectiveLearningCandidate]:
        rows = await self.repository.list_latest_for_user(
            user_id=user_id,
            tenant_id=tenant_id,
            objective_namespace=objective_namespace,
            objective_type=objective_type,
            objective_version=objective_version,
            schema_ref=schema_ref,
            profile_ref=profile_ref,
            profile_version=profile_version,
            extractor_ref=extractor_ref,
            extractor_version=extractor_version,
            status=status,
            approval_status=approval_status,
            validation_passed=validation_passed,
            limit=limit,
            offset=offset,
        )

        return [self.repository.deserialize(row) for row in rows]

    async def get_latest(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> ObjectiveLearningCandidate | None:
        row = await self.repository.get_latest_for_user(
            user_id=user_id,
            candidate_id=candidate_id,
        )

        if row is None:
            return None

        return self.repository.deserialize(row)

    async def history(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> list[ObjectiveLearningCandidate]:
        rows = await self.repository.list_history_for_user(
            user_id=user_id,
            candidate_id=candidate_id,
        )

        return [self.repository.deserialize(row) for row in rows]

    async def review(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
        reviewed_by_user_id: UUID,
        request: ObjectiveLearningCandidateReviewRequest,
    ) -> ObjectiveLearningCandidate | None:
        row = await self.repository.get_latest_for_user(
            user_id=user_id,
            candidate_id=candidate_id,
        )

        if row is None:
            return None

        candidate = self.repository.deserialize(row)

        if (
            candidate.status != ObjectiveLearningCandidateStatus.VALIDATED
            or candidate.approval_status != ObjectiveLearningApprovalStatus.PENDING
        ):
            raise ValueError(
                "Only a pending validated objective learning candidate can be reviewed"
            )

        reviewed = self.factory.review(
            candidate=candidate,
            approved=(request.decision == ObjectiveLearningReviewDecision.APPROVE),
            reviewed_by_user_id=reviewed_by_user_id,
            reason=request.reason,
            reviewed_at=request.reviewed_at,
        )

        appended = await self.repository.append_revision(
            user_id=user_id,
            candidate=reviewed,
        )

        return self.repository.deserialize(appended)


__all__ = [
    "ObjectiveLearningCandidateGenerationItem",
    "ObjectiveLearningCandidateGenerationResult",
    "ObjectiveLearningCandidateReviewRequest",
    "ObjectiveLearningLifecycleOperations",
    "ObjectiveLearningReviewDecision",
]
