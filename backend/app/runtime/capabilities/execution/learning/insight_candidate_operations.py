from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.learning.aggregation import (
    CapabilityLearningAggregationPolicy,
    CapabilityLearningInterpretation,
)
from app.runtime.capabilities.execution.learning.insight_candidate_repository import (
    CapabilityLearningInsightCandidateRepository,
)
from app.runtime.capabilities.execution.learning.insight_candidates import (
    CapabilityLearningApprovalStatus,
    CapabilityLearningCandidateStatus,
    CapabilityLearningInsightCandidate,
    CapabilityLearningInsightCandidateFactory,
    CapabilityLearningInsightPolicy,
    CapabilityLearningPromotionTarget,
)
from app.runtime.capabilities.execution.learning.trend_service import (
    CapabilityLearningTrendService,
)
from app.runtime.capabilities.execution.learning.trends import (
    CapabilityLearningTrendPolicy,
)


class CapabilityLearningReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class CapabilityLearningCandidateGenerateRequest(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None
    capability_id: str | None = None
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    window_hours: int = Field(
        default=168,
        ge=1,
        le=4380,
    )
    minimum_effective_sample_size: float = Field(
        default=5.0,
        gt=0.0,
        le=100_000.0,
    )
    meaningful_success_delta: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
    )
    trend_contradiction_threshold: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
    )

    minimum_summary_confidence: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
    )
    maximum_candidate_contradiction_score: float = (
        Field(
            default=0.20,
            ge=0.0,
            le=1.0,
        )
    )
    require_high_quality: bool = True
    require_stable_trend: bool = True
    approval_required: bool = True

    promotion_target: (
        CapabilityLearningPromotionTarget
    ) = (
        CapabilityLearningPromotionTarget
        .PLANNER_ADVISORY
    )


class CapabilityLearningCandidateReviewRequest(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    decision: CapabilityLearningReviewDecision
    reason: str = Field(
        min_length=1,
        max_length=4000,
    )


class CapabilityLearningCandidateGenerationItem(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    candidate: CapabilityLearningInsightCandidate
    created: bool


class CapabilityLearningCandidateGenerationResult(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    analyzed_reports: int = Field(ge=0)
    eligible_interpretations: int = Field(ge=0)
    created_candidates: int = Field(ge=0)
    existing_candidates: int = Field(ge=0)
    items: tuple[
        CapabilityLearningCandidateGenerationItem,
        ...,
    ] = ()


class CapabilityLearningInsightCandidateOperations:
    """
    Authenticated candidate generation and review operations.

    All persistence is append-only. These operations do not activate learned
    behavior or write planner, provider-selection, health, allocation, or
    runtime-policy state.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            CapabilityLearningInsightCandidateRepository
            | None
        ) = None,
        trend_service: (
            CapabilityLearningTrendService
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or CapabilityLearningInsightCandidateRepository(
                db
            )
        )
        self.trend_service = (
            trend_service
            or CapabilityLearningTrendService(db)
        )

    async def generate(
        self,
        *,
        user_id: UUID,
        request: (
            CapabilityLearningCandidateGenerateRequest
        ),
    ) -> CapabilityLearningCandidateGenerationResult:
        trend_service = self.trend_service

        if type(trend_service) is CapabilityLearningTrendService:
            trend_service = CapabilityLearningTrendService(
                self.db,
                aggregation_policy=(
                    CapabilityLearningAggregationPolicy(
                        minimum_effective_sample_size=(
                            request
                            .minimum_effective_sample_size
                        )
                    )
                ),
                trend_policy=(
                    CapabilityLearningTrendPolicy(
                        meaningful_success_delta=(
                            request
                            .meaningful_success_delta
                        ),
                        contradiction_threshold=(
                            request
                            .trend_contradiction_threshold
                        ),
                    )
                ),
            )

        reports = await trend_service.analyze(
            user_id=user_id,
            tenant_id=request.tenant_id,
            capability_id=request.capability_id,
            provider_id=request.provider_id,
            provider_ref=request.provider_ref,
            action=request.action,
            window_hours=request.window_hours,
        )

        factory = (
            CapabilityLearningInsightCandidateFactory(
                policy=CapabilityLearningInsightPolicy(
                    minimum_summary_confidence=(
                        request
                        .minimum_summary_confidence
                    ),
                    maximum_contradiction_score=(
                        request
                        .maximum_candidate_contradiction_score
                    ),
                    require_high_quality=(
                        request.require_high_quality
                    ),
                    require_stable_trend=(
                        request.require_stable_trend
                    ),
                    approval_required=(
                        request.approval_required
                    ),
                )
            )
        )

        items: list[
            CapabilityLearningCandidateGenerationItem
        ] = []
        eligible_interpretations = 0
        created_candidates = 0
        existing_candidates = 0

        for report in reports:
            if (
                report.recent.interpretation
                not in {
                    CapabilityLearningInterpretation
                    .POSITIVE,
                    CapabilityLearningInterpretation
                    .NEGATIVE,
                }
            ):
                continue

            eligible_interpretations += 1

            candidate = factory.propose(
                report=report,
                promotion_target=(
                    request.promotion_target
                ),
            )

            existing_row = await (
                self.repository
                .get_latest_by_fingerprint_for_user(
                    user_id=user_id,
                    evidence_fingerprint=(
                        candidate
                        .evidence
                        .evidence_fingerprint
                    ),
                )
            )

            if existing_row is not None:
                items.append(
                    CapabilityLearningCandidateGenerationItem(
                        candidate=(
                            self.repository.deserialize(
                                existing_row
                            )
                        ),
                        created=False,
                    )
                )
                existing_candidates += 1
                continue

            row = await self.repository.append_revision(
                user_id=user_id,
                candidate=candidate,
            )

            items.append(
                CapabilityLearningCandidateGenerationItem(
                    candidate=(
                        self.repository.deserialize(row)
                    ),
                    created=True,
                )
            )
            created_candidates += 1

        return (
            CapabilityLearningCandidateGenerationResult(
                analyzed_reports=len(reports),
                eligible_interpretations=(
                    eligible_interpretations
                ),
                created_candidates=(
                    created_candidates
                ),
                existing_candidates=(
                    existing_candidates
                ),
                items=tuple(items),
            )
        )

    async def list_latest(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        action: str | None = None,
        status: str | None = None,
        approval_status: str | None = None,
        promotion_eligible: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CapabilityLearningInsightCandidate]:
        rows = await (
            self.repository.list_latest_for_user(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id=capability_id,
                provider_id=provider_id,
                provider_ref=provider_ref,
                action=action,
                status=status,
                approval_status=approval_status,
                promotion_eligible=(
                    promotion_eligible
                ),
                limit=limit,
                offset=offset,
            )
        )

        return [
            self.repository.deserialize(row)
            for row in rows
        ]

    async def get_latest(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> CapabilityLearningInsightCandidate | None:
        row = await (
            self.repository.get_latest_for_user(
                user_id=user_id,
                candidate_id=candidate_id,
            )
        )

        if row is None:
            return None

        return self.repository.deserialize(row)

    async def history(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> list[CapabilityLearningInsightCandidate]:
        rows = await (
            self.repository.list_history_for_user(
                user_id=user_id,
                candidate_id=candidate_id,
            )
        )

        return [
            self.repository.deserialize(row)
            for row in rows
        ]

    async def review(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
        reviewed_by_user_id: UUID,
        request: (
            CapabilityLearningCandidateReviewRequest
        ),
    ) -> CapabilityLearningInsightCandidate | None:
        row = await (
            self.repository.get_latest_for_user(
                user_id=user_id,
                candidate_id=candidate_id,
            )
        )

        if row is None:
            return None

        candidate = self.repository.deserialize(row)

        if (
            candidate.status
            != CapabilityLearningCandidateStatus
            .VALIDATED
            or candidate.approval_status
            != CapabilityLearningApprovalStatus
            .PENDING
        ):
            raise ValueError(
                "Only a pending validated candidate "
                "can be reviewed"
            )

        reviewed = (
            CapabilityLearningInsightCandidateFactory()
            .review(
                candidate=candidate,
                approved=(
                    request.decision
                    == CapabilityLearningReviewDecision
                    .APPROVE
                ),
                reviewed_by_user_id=(
                    reviewed_by_user_id
                ),
                reason=request.reason,
            )
        )

        appended = await (
            self.repository.append_revision(
                user_id=user_id,
                candidate=reviewed,
            )
        )

        return self.repository.deserialize(appended)


__all__ = [
    "CapabilityLearningCandidateGenerateRequest",
    "CapabilityLearningCandidateGenerationItem",
    "CapabilityLearningCandidateGenerationResult",
    "CapabilityLearningCandidateReviewRequest",
    "CapabilityLearningInsightCandidateOperations",
    "CapabilityLearningReviewDecision",
]
