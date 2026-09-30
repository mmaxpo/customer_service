from typing import Literal

from pydantic import BaseModel


class ShopifyBillingCheckoutRequest(BaseModel):
    plan: Literal["starter", "growth", "pro"]


class ShopifyBillingCheckoutRead(BaseModel):
    provider: Literal["shopify"] = "shopify"
    plan: str
    status: str
    provider_subscription_id: str
    confirmation_url: str


class ShopifyBillingPortalRead(BaseModel):
    provider: Literal["shopify"] = "shopify"
    manage_url: str
