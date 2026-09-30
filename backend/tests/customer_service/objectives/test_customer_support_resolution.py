from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportAction,
    CustomerSupportObjective,
    CustomerSupportObjectiveInterpreter,
    MissingInformation,
)
from app.domains.customer_service.services.support.resolution.customer_support_resolution import (
    CustomerSupportClarificationResolver,
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

CLARIFICATION = (
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


def test_customer_clarification_completes_pending_objective():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        ORIGINAL_MESSAGE
    )

    result = CustomerSupportClarificationResolver().resolve(
        message=CLARIFICATION,
        objective=objective,
        order=_order(),
    )

    assert result.status == "ready_for_review"
    assert result.mutation_allowed is False

    assert result.objective.item_assignments == {
        "refund_item": "101",
        "replacement_item": "102",
    }

    assert result.objective.replacement_address == {
        "formatted": "123 Main Street, Miami, FL 33101"
    }

    assert result.objective.missing_information == []
    assert result.objective.requires_clarification is False

    assert result.resolved_fields == [
        "refund_item",
        "replacement_item",
        "replacement_address",
    ]


def test_partial_customer_answer_remains_interrupted():
    objective = CustomerSupportObjectiveInterpreter().interpret(
        ORIGINAL_MESSAGE
    )

    result = CustomerSupportClarificationResolver().resolve(
        message="Refund the Snowboard.",
        objective=objective,
        order=_order(),
    )

    assert result.status == "awaiting_customer"
    assert result.mutation_allowed is False
    assert result.objective.item_assignments["refund_item"] == "101"
    assert result.objective.item_assignments["replacement_item"] is None
    assert result.objective.replacement_address is None



def test_refund_only_resolution_does_not_require_replacement_fields():
    objective = CustomerSupportObjective(
        order_ref="1003",
        requested_actions=[
            CustomerSupportAction.PARTIAL_REFUND,
        ],
        missing_information=[
            MissingInformation.REFUND_ITEM,
        ],
        requires_clarification=True,
    )

    result = CustomerSupportClarificationResolver().resolve(
        message="Refund the Snowboard.",
        objective=objective,
        order=_order(),
    )

    assert result.status == "ready_for_review"
    assert result.objective.item_assignments["refund_item"] == "101"
    assert result.objective.item_assignments["replacement_item"] is None
    assert result.objective.replacement_address is None
    assert result.objective.missing_information == []
    assert result.objective.requires_clarification is False


def test_replacement_only_resolution_does_not_require_refund_or_address():
    objective = CustomerSupportObjective(
        order_ref="1003",
        requested_actions=[
            CustomerSupportAction.REPLACEMENT,
        ],
        missing_information=[
            MissingInformation.REPLACEMENT_ITEM,
        ],
        requires_clarification=True,
    )

    result = CustomerSupportClarificationResolver().resolve(
        message="Replace the Snowboard Boots.",
        objective=objective,
        order=_order(),
    )

    assert result.status == "ready_for_review"
    assert result.objective.item_assignments["refund_item"] is None
    assert result.objective.item_assignments["replacement_item"] == "102"
    assert result.objective.replacement_address is None
    assert result.objective.missing_information == []
    assert result.objective.requires_clarification is False
