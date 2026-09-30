from app.domains.customer_service.services.support.objective.customer_support_intake import (
    CustomerSupportIntakeService,
)
from app.domains.customer_service.providers.shopify_commerce import (
    ShopifyCommerceOrderAdapter,
)


MESSAGE = (
    "I received both items damaged in order #1003. "
    "I want one item refunded and the other replaced. "
    "Please send the replacement to my new address. "
    "This is urgent."
)


def test_complex_request_produces_read_only_clarification_from_order():
    order = ShopifyCommerceOrderAdapter().adapt(
        {
            "id": 6992274227367,
            "name": "#1003",
            "financial_status": "paid",
            "fulfillment_status": "fulfilled",
            "line_items": [
                {
                    "id": 101,
                    "title": "Snowboard",
                    "variant_title": "158 cm",
                    "quantity": 1,
                },
                {
                    "id": 102,
                    "title": "Snowboard Boots",
                    "variant_title": "Size 10",
                    "quantity": 1,
                },
            ],
        }
    )

    result = CustomerSupportIntakeService().assess(
        message=MESSAGE,
        order=order,
    )

    assert result.mutation_allowed is False
    assert result.objective.order_ref == "1003"
    assert result.objective.requires_clarification is True

    assert result.clarification.required is True
    assert result.clarification.customer_message == (
        "I found order #1003. "
        "The order contains: "
        "1. Snowboard — 158 cm; "
        "2. Snowboard Boots — Size 10. "
        "Which item would you like refunded? "
        "Which item would you like replaced? "
        "What address should we use for the replacement? "
        "No refund, replacement, or shipping change will be made "
        "until these details are confirmed."
    )


def test_intake_never_mutates_without_complete_customer_details():
    result = CustomerSupportIntakeService().assess(
        message=MESSAGE,
        order=None,
    )

    assert result.mutation_allowed is False
    assert result.clarification.required is True
