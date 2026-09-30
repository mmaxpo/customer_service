from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.learning.observations.aggregation import (
    BusinessLearningAggregationPolicy,
    BusinessLearningInterpretation,
)
from app.runtime.learning.observations.insight_candidate_repository import (
    BusinessLearningInsightCandidateRepository,
)
from app.runtime.learning.observations.insight_candidates import (
    BusinessLearningApprovalStatus,
    BusinessLearningCandidateStatus,
    BusinessLearningInsightCandidate,
    BusinessLearningInsightCandidateFactory,
    BusinessLearningInsightPolicy,
)
from app.runtime.learning.observations.trend_service import (
    BusinessLearningTrendService,
)
from app.runtime.learning.observations.trends import (
    BusinessLearningTrendPolicy,
)


class BusinessLearningReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class BusinessLearningCandidateGenerateRequest(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid"
    )

    tenant_id: str | None = None
    objective_namespace: str | None = None
    objective_type: str | None = None
    decision: str | None = None

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
    meaningful_failure_delta: float = Field(
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
    require_high_evidence: bool = True
    require_stable_trend: bool = True
    approval_required: bool = True


class BusinessLearningCandidateReviewRequest(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid"
    )

    decision: BusinessLearningReviewDecision
    reason: str = Field(
        min_length=1,
        max_length=4000,
    )


class BusinessLearningCandidateGenerationItem(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid"
    )

    candidate: BusinessLearningInsightCandidate
    created: bool


class BusinessLearningCandidateGenerationResult(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid"
    )

    analyzed_reports: int = Field(ge=0)
    eligible_interpretations: int = Field(ge=0)
    created_candidates: int = Field(ge=0)
    existing_candidates: int = Field(ge=0)

    items: tuple[
        BusinessLearningCandidateGenerationItem,
        ...,
    ] = ()


class BusinessLearningInsightCandidateOperations:
    """
    Authenticated generation and review operations for
    business-learning candidates.

    Persistence is append-only. These operations do not
    activate recommendations, modify planning, alter
    workflows, change routing or runtime policy, or
    execute business actions.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            BusinessLearningInsightCandidateRepository
            | None
        ) = None,
        trend_service: (
            BusinessLearningTrendService
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or BusinessLearningInsightCandidateRepository(
                db
            )
        )
        self.trend_service = (
            trend_service
            or BusinessLearningTrendService(db)
        )

    async def generate(
        self,
        *,
        user_id: UUID,
        request: BusinessLearningCandidateGenerateRequest,
    ) -> BusinessLearningCandidateGenerationResult:
        trend_service = self.trend_service

        if type(trend_service) is BusinessLearningTrendService:
            trend_service = BusinessLearningTrendService(
                self.db,
                aggregation_policy=(
                    BusinessLearningAggregationPolicy(
                        minimum_effective_sample_size=(
                            request
                            .minimum_effective_sample_size
                        )
                    )
                ),
                trend_policy=(
                    BusinessLearningTrendPolicy(
                        meaningful_success_delta=(
                            request
                            .meaningful_success_delta
                        ),
                        meaningful_failure_delta=(
                            request
                            .meaningful_failure_delta
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
            objective_namespace=(
                request.objective_namespace
            ),
            objective_type=request.objective_type,
            decision=request.decision,
            window_hours=request.window_hours,
        )

        factory = (
            BusinessLearningInsightCandidateFactory(
                policy=BusinessLearningInsightPolicy(
                    minimum_summary_confidence=(
                        request
                        .minimum_summary_confidence
                    ),
                    maximum_contradiction_score=(
                        request
                        .maximum_candidate_contradiction_score
                    ),
                    require_high_evidence=(
                        request.require_high_evidence
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
            BusinessLearningCandidateGenerationItem
        ] = []
        eligible_interpretations = 0
        created_candidates = 0
        existing_candidates = 0

        for report in reports:
            if (
                report.recent.interpretation
                not in {
                    BusinessLearningInterpretation
                    .POSITIVE,
                    BusinessLearningInterpretation
                    .NEGATIVE,
                }
            ):
                continue

            eligible_interpretations += 1

            candidate = factory.propose(
                report=report
            )

            existing_row = await (
                self.repository
                .get_latest_by_fingerprint_for_user(
                    user_id=user_id,
                    evidence_fingerprint=(
                        candidate.evidence
                        .evidence_fingerprint
                    ),
                )
            )

            if existing_row is not None:
                items.append(
                    BusinessLearningCandidateGenerationItem(
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
                BusinessLearningCandidateGenerationItem(
                    candidate=(
                        self.repository.deserialize(
                            row
                        )
                    ),
                    created=True,
                )
            )
            created_candidates += 1

        return BusinessLearningCandidateGenerationResult(
            analyzed_reports=len(reports),
            eligible_interpretations=(
                eligible_interpretations
            ),
            created_candidates=created_candidates,
            existing_candidates=existing_candidates,
            items=tuple(items),
        )

    async def list_latest(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        approval_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BusinessLearningInsightCandidate]:
        rows = await (
            self.repository.list_latest_for_user(
                user_id=user_id,
                tenant_id=tenant_id,
                objective_namespace=(
                    objective_namespace
                ),
                objective_type=objective_type,
                decision=decision,
                status=status,
                approval_status=approval_status,
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
    ) -> BusinessLearningInsightCandidate | None:
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
    ) -> list[BusinessLearningInsightCandidate]:
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
        request: BusinessLearningCandidateReviewRequest,
    ) -> BusinessLearningInsightCandidate | None:
        row = await (
            self.repository.get_latest_for_user(
                user_id=user_id,
                candidate_id=candidate_id,
            )
        )

        if row is None:
            return None

        candidate = self.repository.deserialize(
            row
        )

        if (
            candidate.status
            != BusinessLearningCandidateStatus
            .VALIDATED
            or candidate.approval_status
            != BusinessLearningApprovalStatus
            .PENDING
        ):
            raise ValueError(
                "Only a pending validated business "
                "candidate can be reviewed"
            )

        reviewed = (
            BusinessLearningInsightCandidateFactory()
            .review(
                candidate=candidate,
                approved=(
                    request.decision
                    == BusinessLearningReviewDecision
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

        return self.repository.deserialize(
            appended
        )


__all__ = [
    "BusinessLearningCandidateGenerateRequest",
    "BusinessLearningCandidateGenerationItem",
    "BusinessLearningCandidateGenerationResult",
    "BusinessLearningCandidateReviewRequest",
    "BusinessLearningInsightCandidateOperations",
    "BusinessLearningReviewDecision",
]
