import pytest
from pydantic import ValidationError

from app.domains.customer_service.services.shopify_action_scope import (
    ShopifyActionLineItem,
    ShopifyActionScope,
)


def test_refund_scope_preserves_exact_line_item():
    scope = ShopifyActionScope(
        line_items=[
            ShopifyActionLineItem(
                line_item_id="101",
                quantity=1,
            )
        ]
    )

    assert scope.model_dump(mode="json") == {
        "line_items": [
            {
                "line_item_id": "101",
                "quantity": 1,
                "amount": None,
                "restock_type": "no_restock",
            }
        ],
        "replacement_line_item_id": None,
        "replacement_quantity": None,
        "new_address": None,
        "currency": None,
    }


def test_replacement_scope_preserves_item_and_address():
    scope = ShopifyActionScope(
        replacement_line_item_id="102",
        replacement_quantity=1,
        new_address={
            "formatted": "123 Main Street, Miami, FL 33101"
        },
    )

    assert scope.replacement_line_item_id == "102"
    assert scope.replacement_quantity == 1
    assert scope.new_address == {
        "formatted": "123 Main Street, Miami, FL 33101"
    }


def test_replacement_quantity_requires_item():
    with pytest.raises(
        ValidationError,
        match="replacement_quantity requires",
    ):
        ShopifyActionScope(
            replacement_quantity=1,
        )
