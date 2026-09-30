from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/shopify.py
# ============================================================
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.environment import is_production_environment
from app.core.session import get_db
from app.domains.customer_service.integrations.shopify.lifecycle import (
    InvalidShopifyStateError,
    consume_install_state,
    create_install_state,
    process_compliance_webhook,
    process_commerce_webhook,
    verify_webhook_hmac,
)
from app.domains.customer_service.integrations.shopify.oauth import ShopifyOAuthService
from app.domains.customer_service.integrations.shopify.webhooks import ShopifyWebhookAdapter
from app.domains.customer_service.schemas.shopify import (
    ShopifyActionRead,
    ShopifyActionRequest,
    ShopifyConnectionCreate,
    ShopifyConnectionRead,
    ShopifyConnectionUpdate,
    ShopifyConnectionTestRead,
    ShopifyInstallRead,
    ShopifyInstallRequest,
    ShopifyOAuthCallbackRead,
    ShopifyOrderRead,
    ShopifySupportWorkflowPrepareRead,
    ShopifySupportWorkflowPrepareRequest,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
    require_customer_service_permission,
)
from app.domains.customer_service.services.shopify import ShopifyService
from app.domains.customer_service.repositories.omnichannel import OmnichannelRepository
from app.domains.customer_service.services.shopify_billing import ShopifyBillingService
from app.domains.customer_service.repositories.shopify import ShopifyRepository
from app.integrations.errors import IntegrationError, IntegrationProviderError
from app.tenancy.context import Principal, get_current_principal

shopify_router = APIRouter(tags=["Customer Service - Shopify"])

_SHOPIFY_COMMERCE_TOPICS = {
    "orders/create",
    "orders/updated",
    "orders/cancelled",
    "fulfillments/create",
    "refunds/create",
}


@shopify_router.post(
    "/shopify/connect",
    response_model=ShopifyConnectionRead,
)
async def connect_shopify(
    payload: ShopifyConnectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.integrations.manage")),
):
    if payload.access_token and is_production_environment():
        raise HTTPException(
            status_code=400,
            detail="Raw Shopify access tokens are not accepted in production; use OAuth install.",
        )
    return await ShopifyService(db).connect(
        user_id=current_user.id,
        workspace_id=getattr(current_user, "workspace_id", None),
        shop_domain=payload.shop_domain,
        access_token=payload.access_token,
    )


@shopify_router.get(
    "/shopify/connection",
    response_model=ShopifyConnectionRead | None,
)
async def get_shopify_connection(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    connection = await ShopifyService(db).get_active_connection(user_id=current_user.id)
    return (
        None
        if connection is None
        else await ShopifyService(db).connection_read(connection=connection)
    )


@shopify_router.get("/shopify/connections", response_model=list[ShopifyConnectionRead])
async def list_shopify_connections(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ShopifyService(db)
    return [
        await service.connection_read(connection=row)
        for row in await service.list_connections(user_id=current_user.id)
    ]


@shopify_router.get(
    "/shopify/connections/{connection_id}", response_model=ShopifyConnectionRead
)
async def get_shopify_connection_by_id(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ShopifyService(db)
    return await service.connection_read(
        connection=await service.get_connection(
            user_id=current_user.id, connection_id=connection_id
        )
    )


@shopify_router.patch(
    "/shopify/connections/{connection_id}", response_model=ShopifyConnectionRead
)
async def update_shopify_connection_settings(
    connection_id: UUID,
    payload: ShopifyConnectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.integrations.manage")),
):
    service = ShopifyService(db)
    connection = await service.update_connection_settings(
        user_id=current_user.id,
        connection_id=connection_id,
        business_hours_override=payload.business_hours_override,
        timezone_override=payload.timezone_override,
    )
    return await service.connection_read(connection=connection)


@shopify_router.patch(
    "/shopify/connection",
    response_model=ShopifyConnectionRead,
)
async def update_shopify_connection(
    payload: ShopifyConnectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.integrations.manage")),
):
    if payload.access_token and is_production_environment():
        raise HTTPException(
            status_code=400,
            detail="Raw Shopify access tokens are not accepted in production; use OAuth install.",
        )
    return await ShopifyService(db).connect(
        user_id=current_user.id,
        workspace_id=getattr(current_user, "workspace_id", None),
        shop_domain=payload.shop_domain,
        access_token=payload.access_token,
    )


@shopify_router.delete(
    "/shopify/connection/{connection_id}",
    response_model=ShopifyConnectionRead,
)
async def delete_shopify_connection(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.integrations.manage")),
):
    return await ShopifyService(db).delete_connection(
        user_id=current_user.id,
        connection_id=connection_id,
    )


@shopify_router.post(
    "/shopify/connection/test",
    response_model=ShopifyConnectionTestRead,
)
async def test_shopify_connection(
    connection_id: UUID | None = None,
    order_ref: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.integrations.manage")),
):
    return await ShopifyService(db).test_connection(
        user_id=current_user.id,
        connection_id=connection_id,
        order_ref=order_ref,
    )


@shopify_router.get(
    "/shopify/orders/{order_ref}",
    response_model=ShopifyOrderRead,
)
async def get_order(
    order_ref: str,
    connection_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await ShopifyService(db).get_order(
            user_id=current_user.id,
            connection_id=connection_id,
            order_ref=order_ref,
        )
    except IntegrationProviderError as exc:
        message = str(exc)
        status_code = 424

        if "401" in message or "Invalid API key or access token" in message:
            await ShopifyService(db).repo.mark_reauth_required(
                user_id=current_user.id,
                connection_id=connection_id,
            )
            status_code = 401
            detail = "Shopify connection is no longer authorized. Reconnect the Shopify store."
        else:
            detail = "Could not load Shopify order context."

        raise HTTPException(
            status_code=status_code,
            detail={
                "message": detail,
                "provider": "shopify",
                "order_ref": order_ref,
            },
        ) from exc
    except IntegrationError as exc:
        raise HTTPException(
            status_code=424,
            detail={
                "message": "Shopify integration is temporarily unavailable. Reconnect the store or try again later.",
                "provider": "shopify",
                "order_ref": order_ref,
            },
        ) from exc


@shopify_router.post(
    "/shopify/orders/{order_ref}/actions/{action}",
    response_model=ShopifyActionRead,
)
async def perform_order_action(
    order_ref: str,
    action: str,
    payload: ShopifyActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ShopifyService(db).perform_order_action(
        user_id=current_user.id,
        connection_id=payload.connection_id,
        action=action,
        order_ref=order_ref,
        reason=payload.reason,
        note=payload.note,
        new_address=payload.new_address,
        amount=payload.amount,
        scope=payload.scope.model_dump() if payload.scope else None,
        idempotency_key=payload.idempotency_key,
    )


@shopify_router.post(
    "/shopify/support-workflows/prepare",
    response_model=ShopifySupportWorkflowPrepareRead,
)
async def prepare_support_workflow(
    payload: ShopifySupportWorkflowPrepareRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ShopifyService(db).prepare_support_workflow(
        user_id=current_user.id,
        connection_id=payload.connection_id,
        action=payload.action,
        order_ref=payload.order_ref,
        reason=payload.reason,
        note=payload.note,
        new_address=payload.new_address,
    )


def _shopify_oauth_service() -> ShopifyOAuthService:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return ShopifyOAuthService(
            api_key="dev-shopify-api-key",
            api_secret="dev-shopify-api-secret",
            redirect_uri="http://localhost:8000/customer-service/shopify/oauth/callback",
            scopes=[
                "read_orders",
                "read_draft_orders",
                "read_customers",
                "read_products",
                "write_orders",
                "read_fulfillments",
                "write_draft_orders",
                "read_content",
            ],
        )

    api_key = settings.SHOPIFY_API_KEY or ""
    api_secret = settings.SHOPIFY_API_SECRET or ""
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=503,
            detail=(
                "Shopify OAuth is not configured. Set SHOPIFY_API_KEY and "
                "SHOPIFY_API_SECRET in the server environment."
            ),
        )
    return ShopifyOAuthService(
        api_key=api_key,
        api_secret=api_secret,
        redirect_uri=settings.SHOPIFY_REDIRECT_URI,
        scopes=[
            scope.strip()
            for scope in settings.SHOPIFY_SCOPES.split(",")
            if scope.strip()
        ],
    )


@shopify_router.post(
    "/shopify/install",
    response_model=ShopifyInstallRead,
)
async def start_shopify_install(
    payload: ShopifyInstallRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if principal.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    oauth = _shopify_oauth_service()
    try:
        shop_domain = oauth.normalize_shop_domain(payload.shop_domain)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid Shopify shop") from None
    state = await create_install_state(
        db,
        user_id=principal.user_id,
        workspace_id=principal.workspace_id,
        shop_domain=shop_domain,
    )

    return {
        "shop_domain": shop_domain,
        "install_url": oauth.build_install_url(
            shop_domain=shop_domain,
            state=state,
        ),
        "state": state,
    }


@shopify_router.get("/shopify/install")
async def start_shopify_install_redirect(
    shop: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if principal.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    oauth = _shopify_oauth_service()
    try:
        shop_domain = oauth.normalize_shop_domain(shop)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid Shopify shop") from None
    state = await create_install_state(
        db,
        user_id=principal.user_id,
        workspace_id=principal.workspace_id,
        shop_domain=shop_domain,
    )

    return RedirectResponse(
        oauth.build_install_url(
            shop_domain=shop_domain,
            state=state,
        )
    )


@shopify_router.get(
    "/shopify/oauth/callback",
    response_model=ShopifyOAuthCallbackRead,
)
async def shopify_oauth_callback(
    request: Request,
    shop: str,
    hmac: str,
    code: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    oauth = _shopify_oauth_service()
    shop_domain = oauth.normalize_shop_domain(shop)
    params = dict(request.query_params)

    valid = oauth.verify_hmac(params=params)

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid Shopify callback HMAC")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Incomplete Shopify callback")

    try:
        install = await consume_install_state(
            db,
            state=state,
            shop_domain=shop_domain,
        )
    except InvalidShopifyStateError:
        raise HTTPException(
            status_code=400,
            detail="Invalid, expired, or already used Shopify state",
        ) from None

    token_payload = await oauth.exchange_code_for_access_token(
        shop_domain=shop_domain,
        code=code,
    )

    access_token = token_payload.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=502,
            detail="Shopify OAuth did not return an access token",
        )

    granted = oauth.validate_granted_scopes(token_payload.get("scope"))
    await oauth.register_compliance_webhooks(
        shop_domain=shop_domain,
        access_token=str(access_token),
        api_version=settings.SHOPIFY_API_VERSION,
    )

    connection = await ShopifyService(db).connect(
        user_id=install.workspace_id,
        workspace_id=install.workspace_id,
        shop_domain=shop_domain,
        access_token=str(access_token),
        granted_scopes=",".join(sorted(granted)),
    )

    # OAuth proves consent and gives us a token, but the runtime provider
    # gate also requires a successful live verification before workflows can
    # read orders.  Verify immediately so a newly connected store is usable
    # from Inbox/chat without a separate hidden setup step.
    verification = await ShopifyService(db).test_connection(
        user_id=install.workspace_id,
        connection_id=connection.id,
    )

    # Keep the provider-specific installation and the inbox channel catalog in
    # sync so the Channels page shows the store that was just authorized.
    await OmnichannelRepository(db).create_connection(
        # Channel connections are workspace-scoped in the current product
        # surface, matching the Shopify connection's ownership key.
        user_id=install.workspace_id,
        channel="shopify",
        external_account_id=shop_domain,
        display_name="Main Shopify Store",
        config={"source": "shopify_oauth", "shopify_connection_id": str(connection.id)},
    )
    await db.commit()

    return {
        "shop_domain": shop_domain,
        "valid": True,
        "connected": True,
        "connection_id": connection.id,
        "verified": bool(verification.get("ok")),
    }


@shopify_router.post("/shopify/webhooks", status_code=202)
async def shopify_compliance_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    secret = (
        "dev-shopify-api-secret"
        if os.getenv("PYTEST_CURRENT_TEST")
        else settings.SHOPIFY_API_SECRET or ""
    )
    body = await request.body()
    received_hmac = request.headers.get("x-shopify-hmac-sha256", "")
    if not secret or not verify_webhook_hmac(
        body=body,
        received=received_hmac,
        secret=secret,
    ):
        raise HTTPException(status_code=401, detail="Invalid Shopify webhook HMAC")

    topic = request.headers.get("x-shopify-topic", "")
    if topic not in {
        "app/uninstalled",
        "app_subscriptions/update",
        "customers/data_request",
        "customers/redact",
        "shop/redact",
        *_SHOPIFY_COMMERCE_TOPICS,
    }:
        raise HTTPException(status_code=422, detail="Unsupported Shopify topic")
    try:
        shop_domain = _shopify_oauth_service().normalize_shop_domain(
            request.headers.get("x-shopify-shop-domain", "")
        )
        payload = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid Shopify webhook") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid Shopify webhook payload")

    webhook_id = request.headers.get("x-shopify-webhook-id", "")
    if not webhook_id:
        raise HTTPException(status_code=400, detail="Missing Shopify webhook ID")
    if topic in _SHOPIFY_COMMERCE_TOPICS:
        status = await process_commerce_webhook(
            db,
            webhook_id=webhook_id,
            shop_domain=shop_domain,
            topic=topic,
            payload=payload,
        )
    else:
        status = await process_compliance_webhook(
            db,
            webhook_id=webhook_id,
            shop_domain=shop_domain,
            topic=topic,
            payload=payload,
        )
    if topic == "app_subscriptions/update" and status != "duplicate":
        connection = await ShopifyRepository(db).get_active_connection_by_shop(
            shop_domain=shop_domain
        )
        if connection is not None:
            await ShopifyBillingService(db).sync(workspace_id=connection.user_id)
    return {"status": status}


__all__ = [
    "shopify_router",
]
