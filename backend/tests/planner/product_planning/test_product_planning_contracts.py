from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.tcos.planner.product_planning import (
    ProductPlanningClarification,
    ProductPlanningResult,
)
from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.planner.business_ir.models import (
    BusinessGoal,
    BusinessPlan,
)


def _candidate() -> PlanCandidate:
    return PlanCandidate(
        id="candidate-1",
        source="test",
        business_plan=BusinessPlan(
            id="plan-1",
            goal=BusinessGoal(
                id="goal-1",
                title="Test",
            ),
            tasks=[],
        ),
    )


def test_unclaimed_result_is_valid():
    result = ProductPlanningResult(
        product_id=" Example ",
        claimed=False,
    )

    assert result.product_id == "example"
    assert result.candidates == []
    assert result.clarification is None
    assert result.requires_clarification is False


def test_claimed_result_with_candidates_is_valid():
    candidate = _candidate()

    result = ProductPlanningResult(
        product_id="example",
        claimed=True,
        candidates=[candidate],
    )

    assert result.claimed is True
    assert result.candidates == [candidate]
    assert result.requires_clarification is False


def test_claimed_result_with_clarification_is_valid():
    clarification = ProductPlanningClarification(
        reason_code="missing_order_ref",
        message="Please provide your order number.",
        missing_fields=("order_ref",),
    )

    result = ProductPlanningResult(
        product_id="example",
        claimed=True,
        clarification=clarification,
    )

    assert result.claimed is True
    assert result.candidates == []
    assert result.clarification is clarification
    assert result.requires_clarification is True


def test_unclaimed_result_cannot_contain_candidates():
    with pytest.raises(
        ValidationError,
        match="unclaimed product planning result",
    ):
        ProductPlanningResult(
            product_id="example",
            claimed=False,
            candidates=[_candidate()],
        )


def test_unclaimed_result_cannot_request_clarification():
    with pytest.raises(
        ValidationError,
        match="unclaimed product planning result",
    ):
        ProductPlanningResult(
            product_id="example",
            claimed=False,
            clarification=ProductPlanningClarification(
                reason_code="missing",
                message="Need more information.",
            ),
        )


def test_claimed_result_requires_plan_or_clarification():
    with pytest.raises(
        ValidationError,
        match=("claimed product planning result requires candidates or clarification"),
    ):
        ProductPlanningResult(
            product_id="example",
            claimed=True,
        )


def test_candidates_and_clarification_are_mutually_exclusive():
    with pytest.raises(
        ValidationError,
        match=("cannot contain both candidates and clarification"),
    ):
        ProductPlanningResult(
            product_id="example",
            claimed=True,
            candidates=[_candidate()],
            clarification=ProductPlanningClarification(
                reason_code="missing",
                message="Need more information.",
            ),
        )


@pytest.mark.parametrize(
    "product_id",
    [
        "",
        "   ",
    ],
)
def test_product_id_is_required(product_id):
    with pytest.raises(
        ValidationError,
        match="product_id is required",
    ):
        ProductPlanningResult(
            product_id=product_id,
            claimed=False,
        )
