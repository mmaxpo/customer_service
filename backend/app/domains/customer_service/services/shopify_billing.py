from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException

from app.core.config import settings
from app.core.security.secrets import decrypt_secret
from app.domains.customer_service.integrations.shopify.provider_factory import (
    ShopifyProviderFactory,
)
from app.domains.customer_service.models import WorkspaceSubscription
from app.domains.customer_service.repositories.shopify import ShopifyRepository
from app.domains.customer_service.services.billing_plans import (
    PLAN_CATALOG,
    plan_entitlements,
    plan_from_shopify_name,
)


class ShopifyBillingService:
    def __init__(self, db, *, provider=None):
        self.db = db
        self.provider = provider or ShopifyProviderFactory.create()

    async def checkout(self, *, workspace_id, plan: str) -> dict:
        definition = PLAN_CATALOG.get(plan)
        if definition is None:
            raise HTTPException(status_code=422, detail="Unknown billing plan")
        connection = await self._connection(workspace_id)
        created = await self.provider.create_app_subscription(
            shop_domain=connection.shop_domain,
            access_token=decrypt_secret(connection.access_token_encrypted),
            name=definition["shopify_name"],
            amount=definition["amount"],
            currency=definition["currency"],
            interval=definition["interval"],
            return_url=settings.BILLING_SUCCESS_URL,
            trial_days=settings.DEFAULT_TRIAL_DAYS,
            test=settings.SHOPIFY_BILLING_TEST,
        )
        row = await self._subscription(workspace_id)
        row.plan = plan
        row.status = "pending"
        row.provider = "shopify"
        row.provider_customer_id = connection.shop_domain
        row.provider_subscription_id = created["id"]
        # Pending checkout never grants paid entitlements.
        await self.db.commit()
        return {
            "provider": "shopify",
            "plan": plan,
            "status": "pending",
            "provider_subscription_id": created["id"],
            "confirmation_url": created["confirmation_url"],
        }

    async def sync(self, *, workspace_id):
        connection = await self._connection(workspace_id)
        subscriptions = await self.provider.get_active_app_subscriptions(
            shop_domain=connection.shop_domain,
            access_token=decrypt_secret(connection.access_token_encrypted),
        )
        row = await self._subscription(workspace_id)
        recognized = next(
            (
                (item, plan_from_shopify_name(str(item.get("name") or "")))
                for item in subscriptions
                if plan_from_shopify_name(str(item.get("name") or ""))
            ),
            None,
        )
        if recognized is None:
            if row.provider == "shopify":
                row.status = "canceled"
                row.entitlements = {}
                row.cancel_at_period_end = False
                await self.db.commit()
            return row
        provider_subscription, plan = recognized
        row.plan = plan
        row.status = "active"
        row.provider = "shopify"
        row.provider_customer_id = connection.shop_domain
        row.provider_subscription_id = provider_subscription["id"]
        row.entitlements = plan_entitlements(plan)
        period_end = provider_subscription.get("currentPeriodEnd")
        row.current_period_ends_at = (
            datetime.fromisoformat(str(period_end).replace("Z", "+00:00"))
            if period_end
            else None
        )
        row.cancel_at_period_end = False
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def cancel(self, *, workspace_id):
        row = await self._subscription(workspace_id)
        if row.provider != "shopify" or not row.provider_subscription_id:
            raise HTTPException(
                status_code=409, detail="No Shopify subscription to cancel"
            )
        connection = await self._connection(workspace_id)
        canceled = await self.provider.cancel_app_subscription(
            shop_domain=connection.shop_domain,
            access_token=decrypt_secret(connection.access_token_encrypted),
            subscription_id=row.provider_subscription_id,
        )
        row.status = "canceled"
        row.entitlements = {}
        row.cancel_at_period_end = False
        await self.db.commit()
        return canceled

    async def portal(self, *, workspace_id) -> dict:
        connection = await self._connection(workspace_id)
        shop_handle = connection.shop_domain.removesuffix(".myshopify.com")
        return {
            "provider": "shopify",
            "manage_url": (
                f"https://admin.shopify.com/store/{shop_handle}/settings/billing/subscriptions"
            ),
        }

    async def _connection(self, workspace_id):
        connection = await ShopifyRepository(self.db).get_active_connection(
            user_id=workspace_id
        )
        if connection is None or connection.reauth_required_at is not None:
            raise HTTPException(
                status_code=409, detail="Reconnect Shopify before billing"
            )
        return connection

    async def _subscription(self, workspace_id):
        row = await self.db.get(WorkspaceSubscription, workspace_id)
        if row is None:
            row = WorkspaceSubscription(
                workspace_id=workspace_id,
                plan="trial",
                status="trialing",
                entitlements={},
            )
            self.db.add(row)
            await self.db.flush()
        return row
