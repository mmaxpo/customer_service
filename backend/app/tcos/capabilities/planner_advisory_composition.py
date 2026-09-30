from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.learning import (
    CapabilityPlannerAdvisory,
    CapabilityPlannerAdvisoryService,
)
from app.tcos.capabilities.models import (
    CapabilityDefinition,
)
from app.tcos.capabilities.planner import (
    CapabilityMatch,
    CapabilityMatchRequest,
    match_capabilities,
)
from app.tcos.capabilities.planner_advisory_policy import (
    CapabilityPlannerAdvisoryContext,
    CapabilityPlannerAdvisoryPolicy,
)
from app.tcos.capabilities.planner_advisory_renderer import (
    CapabilityPlannerAdvisoryRenderer,
    CapabilityPlannerRenderedContext,
)


class CapabilityAdvisoryMatchRequest(
    CapabilityMatchRequest
):
    """
    Authenticated planner request with an explicit advisory scope.

    The inherited planner fields retain their current behavior. Additional
    fields are used only to retrieve exact-scope read-only advisories.
    """

    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    advisory_limit_per_match: int = Field(
        default=100,
        ge=1,
        le=500,
    )


class CapabilityAdvisoryMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: CapabilityDefinition
    score: float
    compatible: bool
    reasons: list[str] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(
        default_factory=list
    )
    advisories: list[
        CapabilityPlannerAdvisory
    ] = Field(default_factory=list)
    advisory_context: (
        CapabilityPlannerAdvisoryContext
    ) = Field(
        default_factory=(
            CapabilityPlannerAdvisoryContext
        )
    )
    rendered_advisory_context: (
        CapabilityPlannerRenderedContext
    ) = Field(
        default_factory=lambda: (
            CapabilityPlannerRenderedContext(
                present=False,
                text="",
            )
        )
    )


class CapabilityAdvisoryMatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    matches: list[CapabilityAdvisoryMatch]

    ranking_affected_by_advisories: bool = False


class CapabilityPlannerAdvisoryComposer:
    """
    Composes the existing planner response with read-only learning context.

    It never changes planner scores, compatibility, candidate inclusion,
    ordering, limits, provider selection, or execution authorization.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        advisory_service: (
            CapabilityPlannerAdvisoryService
            | None
        ) = None,
        advisory_policy: (
            CapabilityPlannerAdvisoryPolicy
            | None
        ) = None,
        advisory_renderer: (
            CapabilityPlannerAdvisoryRenderer
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.advisory_service = (
            advisory_service
            or CapabilityPlannerAdvisoryService(
                db
            )
        )
        self.advisory_policy = (
            advisory_policy
            or CapabilityPlannerAdvisoryPolicy()
        )
        self.advisory_renderer = (
            advisory_renderer
            or CapabilityPlannerAdvisoryRenderer()
        )

    async def compose(
        self,
        *,
        user_id: UUID,
        request: CapabilityAdvisoryMatchRequest,
    ) -> CapabilityAdvisoryMatchResponse:
        planner_request = CapabilityMatchRequest(
            **request.model_dump(
                exclude={
                    "tenant_id",
                    "provider_id",
                    "provider_ref",
                    "action",
                    "advisory_limit_per_match",
                },
                mode="python",
            )
        )

        base_response = match_capabilities(
            planner_request
        )

        composed: list[
            CapabilityAdvisoryMatch
        ] = []

        for match in base_response.matches:
            advisories = await (
                self.advisory_service
                .list_for_scope(
                    user_id=user_id,
                    tenant_id=request.tenant_id,
                    capability_id=(
                        match.capability.id
                    ),
                    provider_id=(
                        request.provider_id
                    ),
                    provider_ref=(
                        request.provider_ref
                    ),
                    action=request.action,
                    limit=(
                        request
                        .advisory_limit_per_match
                    ),
                )
            )

            advisory_context = (
                self.advisory_policy
                .consume(advisories)
            )

            composed.append(
                _compose_match(
                    match=match,
                    advisories=advisories,
                    advisory_context=(
                        advisory_context
                    ),
                    rendered_advisory_context=(
                        self.advisory_renderer
                        .render(advisory_context)
                    ),
                )
            )

        return CapabilityAdvisoryMatchResponse(
            query=base_response.query,
            matches=composed,
            ranking_affected_by_advisories=False,
        )


def _compose_match(
    *,
    match: CapabilityMatch,
    advisories: list[
        CapabilityPlannerAdvisory
    ],
    advisory_context: (
        CapabilityPlannerAdvisoryContext
    ),
    rendered_advisory_context: (
        CapabilityPlannerRenderedContext
    ),
) -> CapabilityAdvisoryMatch:
    return CapabilityAdvisoryMatch(
        capability=match.capability,
        score=match.score,
        compatible=match.compatible,
        reasons=list(match.reasons),
        warnings=list(match.warnings),
        advisories=advisories,
        advisory_context=advisory_context,
        rendered_advisory_context=(
            rendered_advisory_context
        ),
    )


__all__ = [

    "CapabilityAdvisoryMatch",
    "CapabilityAdvisoryMatchRequest",
    "CapabilityAdvisoryMatchResponse",
    "CapabilityPlannerAdvisoryComposer",
]
