from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
)
from app.tcos.planner.business_ir.models import BusinessPlan


class PlannerIntentName(StrEnum):
    CUSTOMER_REPLY = "customer_reply"
    UNKNOWN = "unknown"


class PlannerIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: PlannerIntentName
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )
    entities: dict = Field(default_factory=dict)
    needs_clarification: bool = False


class PlanningContext(BaseModel):
    """
    Information available before planning begins.

    This is a public planning-boundary contract. Product planners may
    consume it without depending on TCOS planner runtime internals.
    """

    model_config = ConfigDict(extra="forbid")

    user_message: str = ""

    channel: str | None = None

    customer_id: str | None = None

    conversation_id: str | None = None

    objective_context: ObjectiveCognitiveContext | None = None

    enabled_capabilities: list[str] = Field(
        default_factory=list
    )

    planner_preferences: dict = Field(
        default_factory=dict
    )

    execution_constraints: dict = Field(
        default_factory=dict
    )


class PlanCandidate(BaseModel):
    """
    One possible way to solve the user's goal.

    This is part of the public product-planning extension contract,
    not an implementation detail of the planner runtime.
    """

    model_config = ConfigDict(extra="forbid")

    id: str

    source: str

    business_plan: BusinessPlan

    score: float = 0.0

    explanation: str = ""

    metrics: dict = Field(default_factory=dict)


class ProductPlanningClarification(BaseModel):
    """
    Product-owned request for missing information.

    Clarification is a planning result, not executable work. It must
    therefore never be represented as a provider call or workflow
    merely to fit the planning contract.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    reason_code: str
    message: str

    missing_fields: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductPlanningResult(BaseModel):
    """
    Result returned by one product planner.

    There are three valid states:

    1. unclaimed
       The product does not own the request.

    2. planned
       The product owns the request and produced candidate plans.

    3. clarification
       The product owns the request but requires more information
       before executable planning may continue.
    """

    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    product_id: str

    claimed: bool = False

    candidates: list[PlanCandidate] = Field(default_factory=list)

    clarification: ProductPlanningClarification | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_state(self) -> "ProductPlanningResult":
        normalized_product_id = self.product_id.strip().lower()

        if not normalized_product_id:
            raise ValueError("product_id is required")

        self.product_id = normalized_product_id

        if not self.claimed:
            if self.candidates:
                raise ValueError(
                    "unclaimed product planning result cannot "
                    "contain candidates"
                )

            if self.clarification is not None:
                raise ValueError(
                    "unclaimed product planning result cannot "
                    "request clarification"
                )

            return self

        has_candidates = bool(self.candidates)
        has_clarification = self.clarification is not None

        if has_candidates and has_clarification:
            raise ValueError(
                "product planning result cannot contain both "
                "candidates and clarification"
            )

        if not has_candidates and not has_clarification:
            raise ValueError(
                "claimed product planning result requires "
                "candidates or clarification"
            )

        return self

    @property
    def requires_clarification(self) -> bool:
        return self.clarification is not None


@runtime_checkable
class ProductPlanner(Protocol):
    """
    Product-owned initial-planning boundary.

    The autonomous Core defines this contract but does not implement
    product business semantics.

    A product planner may:

    - decline ownership of a request,
    - return one or more BusinessPlan candidates, or
    - claim the request and request clarification.

    It must not execute workflows or provider operations.
    """

    @property
    def product_id(self) -> str:
        """Stable product identifier used for registration."""

    def plan(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None = None,
    ) -> ProductPlanningResult:
        """Interpret and plan one request for this product."""


__all__ = [
    "PlanCandidate",
    "PlannerIntent",
    "PlannerIntentName",
    "PlanningContext",
    "ProductPlanner",
    "ProductPlanningClarification",
    "ProductPlanningResult",
]
