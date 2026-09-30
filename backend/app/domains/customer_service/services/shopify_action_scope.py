from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ShopifyActionLineItem(BaseModel):
    line_item_id: str
    quantity: int = Field(default=1, ge=1)
    amount: str | None = None
    restock_type: Literal["no_restock", "cancel", "return"] = "no_restock"


class ShopifyActionScope(BaseModel):
    """
    Structured scope for a Shopify mutation.

    This model describes exactly which parts of an order an approved
    operation targets. It does not itself authorize or execute anything.
    """

    line_items: list[ShopifyActionLineItem] = Field(default_factory=list)
    replacement_line_item_id: str | None = None
    replacement_quantity: int | None = Field(
        default=None,
        ge=1,
    )
    new_address: dict | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_replacement_quantity(self):
        if (
            self.replacement_quantity is not None
            and self.replacement_line_item_id is None
        ):
            raise ValueError("replacement_quantity requires replacement_line_item_id")

        return self
