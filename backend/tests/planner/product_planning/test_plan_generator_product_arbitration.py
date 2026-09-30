from __future__ import annotations

from app.tcos.planner.operations import (
    OperationType,
    PlanningOperation,
)
from app.tcos.planner.product_planning import (
    ProductPlannerRegistry,
    ProductPlanningClarification,
    ProductPlanningResult,
)
from app.tcos.planner.runtime.business_plan_builder import (
    BusinessPlanBuilder,
)
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.plan_candidate import (
    PlanCandidate,
)
from app.tcos.planner.runtime.plan_generator import (
    PlanGenerator,
)
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


def _candidate(
    *,
    candidate_id: str,
    product_id: str,
) -> PlanCandidate:
    plan = BusinessPlanBuilder().from_operations(
        plan_id=f"{product_id}_plan",
        goal_title=f"{product_id}.goal",
        operations=[
            PlanningOperation(
                id="respond",
                capability_id="runtime.response",
                operation_type=OperationType.COMMUNICATE,
                purpose="Respond.",
            )
        ],
    )

    return PlanCandidate(
        id=candidate_id,
        source=f"{product_id}_product_planner",
        business_plan=plan,
        score=0.0,
        explanation="Product-owned plan.",
        metrics={
            "product_id": product_id,
        },
    )


class UnclaimedPlanner:
    product_id = "aaa_unclaimed"

    def plan(self, *, intent, context=None):
        del intent, context

        return ProductPlanningResult(
            product_id=self.product_id,
            claimed=False,
        )


class PlannedPlanner:
    product_id = "bbb_planned"

    def plan(self, *, intent, context=None):
        del intent, context

        return ProductPlanningResult(
            product_id=self.product_id,
            claimed=True,
            candidates=[
                _candidate(
                    candidate_id="product_candidate",
                    product_id=self.product_id,
                )
            ],
        )


class ClarificationPlanner:
    product_id = "bbb_clarification"

    def plan(self, *, intent, context=None):
        del intent, context

        return ProductPlanningResult(
            product_id=self.product_id,
            claimed=True,
            clarification=(
                ProductPlanningClarification(
                    reason_code="missing_reference",
                    message="Please provide the reference.",
                    missing_fields=("reference",),
                )
            ),
        )


class MustNotRunPlanner:
    product_id = "zzz_must_not_run"

    def __init__(self):
        self.called = False

    def plan(self, *, intent, context=None):
        del intent, context
        self.called = True

        raise AssertionError("Planner after first claim must not run")


def _context(message: str):
    context = build_default_planning_context(
        user_message=message,
    )

    return (
        detect_intent(text=context.user_message),
        context,
    )


def test_unclaimed_product_falls_back_to_legacy_reasoner():
    registry = ProductPlannerRegistry()
    registry.register(UnclaimedPlanner())

    intent, context = _context("Summarize https://example.com")

    result = PlanGenerator(
        product_planners=registry,
    ).generate_result(
        intent=intent,
        context=context,
    )

    assert result.product_result is None
    assert result.product_claimed is False
    assert result.requires_clarification is False

    assert result.candidates
    assert result.candidates[0].source == ("capability_reasoner")


def test_first_claimed_product_candidate_is_authoritative():
    registry = ProductPlannerRegistry()

    registry.register(UnclaimedPlanner())
    registry.register(PlannedPlanner())

    must_not_run = MustNotRunPlanner()
    registry.register(must_not_run)

    intent, context = _context("Reply to customer")

    result = PlanGenerator(
        product_planners=registry,
    ).generate_result(
        intent=intent,
        context=context,
    )

    assert result.product_claimed is True
    assert result.requires_clarification is False

    assert len(result.candidates) == 1

    assert result.candidates[0].id == ("product_candidate")

    assert result.candidates[0].source == ("bbb_planned_product_planner")

    assert must_not_run.called is False


def test_claimed_clarification_blocks_legacy_fallback():
    registry = ProductPlannerRegistry()

    registry.register(UnclaimedPlanner())
    registry.register(ClarificationPlanner())

    must_not_run = MustNotRunPlanner()
    registry.register(must_not_run)

    intent, context = _context("Reply to customer: Where is my order?")

    result = PlanGenerator(
        product_planners=registry,
    ).generate_result(
        intent=intent,
        context=context,
    )

    assert result.product_claimed is True
    assert result.requires_clarification is True
    assert result.candidates == []

    assert result.product_result is not None
    assert result.product_result.clarification is not None

    assert result.product_result.clarification.reason_code == "missing_reference"

    assert must_not_run.called is False


def test_legacy_generate_api_refuses_to_hide_clarification():
    registry = ProductPlannerRegistry()
    registry.register(ClarificationPlanner())

    intent, context = _context("Reply to customer: Where is my order?")

    generator = PlanGenerator(
        product_planners=registry,
    )

    try:
        generator.generate(
            intent=intent,
            context=context,
        )
    except ValueError as exc:
        assert "requires clarification" in str(exc)
    else:
        raise AssertionError(
            "generate() must not silently collapse clarification into fallback"
        )
