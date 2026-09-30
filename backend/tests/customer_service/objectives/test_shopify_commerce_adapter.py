from app.domains.customer_service.providers.shopify_commerce import (
    ShopifyCommerceOrderAdapter,
)


def test_shopify_order_is_normalized_to_generic_commerce_order():
    order = ShopifyCommerceOrderAdapter().adapt(
        {
            "id": 6992274227367,
            "name": "#1003",
            "financial_status": "paid",
            "fulfillment_status": "fulfilled",
            "line_items": [
                {
                    "id": 101,
                    "product_id": 201,
                    "variant_id": 301,
                    "title": "Snowboard",
                    "variant_title": "158 cm",
                    "sku": "BOARD-158",
                    "quantity": 1,
                    "fulfillment_status": "fulfilled",
                },
                {
                    "id": 102,
                    "product_id": 202,
                    "variant_id": 302,
                    "title": "Snowboard Boots",
                    "variant_title": "Size 10",
                    "sku": "BOOTS-10",
                    "quantity": 1,
                    "fulfillment_status": "fulfilled",
                },
            ],
        }
    )

    assert order.provider == "shopify"
    assert order.provider_order_id == "6992274227367"
    assert order.order_ref == "#1003"
    assert order.financial_status == "paid"
    assert order.fulfillment_status == "fulfilled"

    assert len(order.line_items) == 2

    assert order.line_items[0].title == "Snowboard"
    assert order.line_items[0].variant_title == "158 cm"
    assert order.line_items[0].sku == "BOARD-158"
    assert order.line_items[0].quantity == 1

    assert order.line_items[1].title == "Snowboard Boots"
    assert order.line_items[1].variant_title == "Size 10"


def test_shopify_adapter_ignores_invalid_items_safely():
    order = ShopifyCommerceOrderAdapter().adapt(
        {
            "id": "1003",
            "name": "#1003",
            "line_items": [
                None,
                {},
                {"quantity": 2},
                {"title": "Valid item", "quantity": "2"},
            ],
        }
    )

    assert len(order.line_items) == 1
    assert order.line_items[0].title == "Valid item"
    assert order.line_items[0].quantity == 2
