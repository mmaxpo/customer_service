from uuid import uuid4

import pytest

from app.core.security.secrets import encrypt_secret
from app.core.session import SessionLocal
from app.domains.customer_service.models import CustomerServiceShopifyConnection
from app.domains.customer_service.services.shopify_billing import ShopifyBillingService
from app.identity import create_user
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


class BillingProvider:
    def __init__(self):
        self.active = []

    async def create_app_subscription(self, **kwargs):
        assert kwargs["name"] == "Tajeran Growth"
        return {
            "id": "gid://shopify/AppSubscription/123",
            "confirmation_url": "https://shop.myshopify.com/confirm/123",
        }

    async def get_active_app_subscriptions(self, **kwargs):
        return self.active

    async def cancel_app_subscription(self, **kwargs):
        return {"id": kwargs["subscription_id"], "status": "CANCELLED"}


async def merchant_with_shopify(db):
    user = await create_user(
        UserCreate(
            email=f"billing-{uuid4()}@example.com",
            password=f"Billing-{uuid4()}",
            terms_accepted=True,
            terms_version="v1",
            privacy_accepted=True,
            privacy_version="v1",
        ),
        db,
    )
    workspace, _ = await WorkspaceService(db).create_workspace(
        user_id=user.id,
        payload=WorkspaceCreate(name=f"Billing {uuid4()}"),
    )
    db.add(
        CustomerServiceShopifyConnection(
            user_id=workspace.id,
            workspace_id=workspace.id,
            shop_domain="billing-test.myshopify.com",
            access_token_encrypted=encrypt_secret("shop-token"),
            status="active",
        )
    )
    await db.commit()
    return workspace


@pytest.mark.asyncio
async def test_checkout_does_not_grant_entitlements_until_shopify_verifies():
    provider = BillingProvider()
    async with SessionLocal() as db:
        workspace = await merchant_with_shopify(db)
        service = ShopifyBillingService(db, provider=provider)
        checkout = await service.checkout(workspace_id=workspace.id, plan="growth")

        assert checkout["status"] == "pending"
        subscription = await service._subscription(workspace.id)
        assert subscription.entitlements == {}

        provider.active = [
            {
                "id": "gid://shopify/AppSubscription/123",
                "name": "Tajeran Growth",
                "status": "ACTIVE",
                "currentPeriodEnd": "2026-10-01T00:00:00Z",
            }
        ]
        subscription = await service.sync(workspace_id=workspace.id)

        assert subscription.status == "active"
        assert subscription.plan == "growth"
        assert subscription.entitlements["monthly_conversations"] == 5000


@pytest.mark.asyncio
async def test_unknown_shopify_subscription_never_grants_entitlements():
    provider = BillingProvider()
    provider.active = [
        {
            "id": "gid://shopify/AppSubscription/untrusted",
            "name": "Frontend Admin Plan",
            "status": "ACTIVE",
        }
    ]
    async with SessionLocal() as db:
        workspace = await merchant_with_shopify(db)
        subscription = await ShopifyBillingService(db, provider=provider).sync(
            workspace_id=workspace.id
        )

        assert subscription.entitlements == {}
        assert subscription.status == "trialing"
