from __future__ import annotations

from pydantic import BaseModel, Field


class CommerceLineItem(BaseModel):
    provider_item_id: str | None = None
    product_id: str | None = None
    variant_id: str | None = None

    title: str
    variant_title: str | None = None
    sku: str | None = None

    quantity: int = 1
    fulfillment_status: str | None = None


class CommerceOrder(BaseModel):
    provider: str
    provider_order_id: str
    order_ref: str | None = None

    financial_status: str | None = None
    fulfillment_status: str | None = None

    line_items: list[CommerceLineItem] = Field(default_factory=list)
