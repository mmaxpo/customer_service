from typing import Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domains.customer_service.services.shopify_action_scope import (
    ShopifyActionScope,
)


class ShopifyConnectionCreate(BaseModel):
    shop_domain: str
    access_token: str | None = None


class ShopifyConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_domain: str
    status: str
    created_at: datetime
    granted_scopes: str | None = None
    installed_at: datetime | None = None
    reauth_required_at: datetime | None = None
    business_hours_override: dict | None = None
    timezone_override: str | None = None
    effective_business_hours: dict | None = None
    effective_timezone: str | None = None


class ShopifyConnectionUpdate(BaseModel):
    business_hours_override: dict | None = None
    timezone_override: str | None = None


class ShopifyOrderRead(BaseModel):
    order_id: str
    order_name: str | None = None
    customer_email: str | None = None
    payload: dict
    context: dict[str, Any] | None = None
    connection_id: UUID | None = None


class ShopifyActionRequest(BaseModel):
    connection_id: UUID | None = None
    order_ref: str | None = None
    reason: str | None = None
    note: str | None = None
    new_address: dict | None = None
    amount: str | None = None
    scope: ShopifyActionScope | None = None
    idempotency_key: str | None = None


class ShopifyActionRead(BaseModel):
    action: str
    order_id: str
    order_name: str | None = None
    status: str
    message: str
    payload: dict


class ShopifySupportWorkflowPrepareRequest(BaseModel):
    connection_id: UUID | None = None
    action: str
    order_ref: str
    reason: str | None = None
    note: str | None = None
    new_address: dict[str, Any] | None = None


class ShopifySupportWorkflowPrepareRead(BaseModel):
    action: str
    order_id: str
    order_name: str | None = None
    context: dict[str, Any]
    workflow: dict[str, Any]


class ShopifyInstallRequest(BaseModel):
    shop_domain: str


class ShopifyInstallRead(BaseModel):
    shop_domain: str
    install_url: str
    state: str


class ShopifyOAuthCallbackRead(BaseModel):
    shop_domain: str
    valid: bool
    connected: bool = False
    verified: bool = False
    connection_id: UUID | None = None


class ShopifyConnectionTestRead(BaseModel):
    ok: bool
    shop_domain: str | None = None
    message: str
    order_ref: str | None = None
    order_name: str | None = None
