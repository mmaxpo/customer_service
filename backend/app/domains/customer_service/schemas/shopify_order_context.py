from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ShopifyTrackingInfo(BaseModel):
    tracking_number: str | None = None
    tracking_url: str | None = None
    carrier: str | None = None
    status: str | None = None


class ShopifyOrderContext(BaseModel):
    order_id: str
    order_name: str | None = None
    customer_email: str | None = None

    financial_status: str | None = None
    fulfillment_status: str | None = None

    total_price: str | None = None
    currency: str | None = None

    shipping_address: dict[str, Any] | None = None
    tracking: ShopifyTrackingInfo = Field(default_factory=ShopifyTrackingInfo)

    is_paid: bool = False
    is_fulfilled: bool = False
    can_refund: bool = False
    can_cancel: bool = False
    can_change_address: bool = False

    raw: dict[str, Any]
