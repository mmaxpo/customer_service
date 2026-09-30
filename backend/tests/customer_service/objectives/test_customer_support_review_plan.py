import pytest

from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportAction,
    CustomerSupportObjective,
    CustomerSupportObjectiveInterpreter,
)
from app.domains.customer_service.services.support.resolution.customer_support_resolution import (
    CustomerSupportClarificationResolver,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    CustomerSupportReviewPlanBuilder,
)
from app.domains.customer_service.providers.shopify_commerce import (
    ShopifyCommerceOrderAdapter,
)


ORIGINAL_MESSAGE = (
    "I received both items damaged in order #1003. "
    "I want one item refunded and the other replaced. "
    "Please send the replacement to my new address. "
    "This is urgent."
)

CLARIFICATION_MESSAGE = (
    "Refund the Snowboard and replace the Snowboard Boots. "
    "Send the replacement to: "
    "123 Main Street, Miami, FL 33101."
)


def _order():
    return ShopifyCommerceOrderAdapter().adapt(
        {
            "id": "6992274227367",
            "name": "#1003",
            "financial_status": "paid",
            "fulfillment_status": "fulfilled",
            "line_items": [
                {
                    "id": "101",
                    "title": "Snowboard",
                    "variant_title": "158 cm",
                    "quantity": 1,
                },
                {
                    "id": "102",
                    "title": "Snowboard Boots",
                    "variant_title": "Size 10",
                    "quantity": 1,
                },
            ],
        }
    )


def _completed_objective():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        ORIGINAL_MESSAGE
    )

    return CustomerSupportClarificationResolver().resolve(
        message=CLARIFICATION_MESSAGE,
        objective=objective,
        order=_order(),
    ).objective


def test_completed_objective_builds_guarded_review_plan():
    plan = CustomerSupportReviewPlanBuilder().build(
        objective=_completed_objective(),
        order=_order(),
        source_objective_version=1,
    )

    assert plan.status == "awaiting_human_review"
    assert plan.order_ref == "#1003"
    assert plan.provider == "shopify"
    assert plan.provider_order_id == "6992274227367"

    assert plan.approval_required is True
    assert plan.execution_allowed is False
    assert plan.source_objective_version == 1

    assert [
        operation.operation_type.value
        for operation in plan.operations
    ] == [
        "partial_refund",
        "replacement",
        "replacement_address",
    ]

    refund, replacement, address = plan.operations

    assert refund.item_id == "101"
    assert refund.item_label == "Snowboard"
    assert refund.approval_required is True
    assert refund.execution_allowed is False

    assert replacement.item_id == "102"
    assert replacement.item_label == "Snowboard Boots"
    assert replacement.approval_required is True
    assert replacement.execution_allowed is False

    assert address.address == {
        "formatted": "123 Main Street, Miami, FL 33101"
    }
    assert address.approval_required is True
    assert address.execution_allowed is False


def test_incomplete_objective_cannot_build_review_plan():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        ORIGINAL_MESSAGE
    )

    with pytest.raises(
        ValueError,
        match="incomplete objective",
    ):
        CustomerSupportReviewPlanBuilder().build(
            objective=objective,
            order=_order(),
        )



def test_whole_order_refund_builds_provider_neutral_review_operation():
    objective = CustomerSupportObjective(
        order_ref="1003",
        requested_actions=[
            CustomerSupportAction.WHOLE_REFUND,
        ],
        requires_clarification=False,
        mutation_allowed=False,
    )

    plan = CustomerSupportReviewPlanBuilder().build(
        objective=objective,
        order=_order(),
    )

    assert len(plan.operations) == 1

    operation = plan.operations[0]

    assert operation.operation_type.value == "whole_refund"
    assert operation.item_id is None
    assert operation.item_label is None
    assert operation.approval_required is True
    assert operation.execution_allowed is False
