from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.services.shopify_provider_installation import (
    ShopifyProviderInstallationProjector,
)
from app.runtime.capabilities.execution.installation.repository import (
    DatabaseProviderInstallationReader,
)


@pytest.mark.asyncio
async def test_shopify_projection_lifecycle():
    user_id = uuid4()
    connection_id = uuid4()

    async with SessionLocal() as db:
        projector = (
            ShopifyProviderInstallationProjector(
                db
            )
        )
        reader = DatabaseProviderInstallationReader(
            db
        )

        connected = await projector.project_connected(
            user_id=user_id,
            connection_id=connection_id,
            shop_domain="example.myshopify.com",
            has_access_token=True,
        )
        await db.commit()

        assert connected.version == 1

        snapshot = await (
            reader.get_provider_installation(
                user_id=user_id,
                tenant_id=None,
                provider_id="shopify",
            )
        )

        assert snapshot.found is True
        assert snapshot.available is False
        assert (
            snapshot.rejection_reason(
                requires_auth=True
            )
            == "provider_configuration_unverified"
        )

        verified = await projector.project_verified(
            user_id=user_id,
            connection_id=connection_id,
            shop_domain="example.myshopify.com",
        )
        await db.commit()

        assert verified.version == 2

        snapshot = await (
            reader.get_provider_installation(
                user_id=user_id,
                tenant_id=None,
                provider_id="shopify",
            )
        )

        assert snapshot.available is True

        disconnected = (
            await projector.project_disconnected(
                user_id=user_id,
                connection_id=connection_id,
                shop_domain=(
                    "example.myshopify.com"
                ),
            )
        )
        await db.commit()

        assert disconnected.version == 3

        snapshot = await (
            reader.get_provider_installation(
                user_id=user_id,
                tenant_id=None,
                provider_id="shopify",
            )
        )

        assert snapshot.available is False
        assert (
            snapshot.rejection_reason(
                requires_auth=True
            )
            == "provider_disabled"
        )


@pytest.mark.asyncio
async def test_shopify_projection_does_not_store_token():
    user_id = uuid4()

    async with SessionLocal() as db:
        await (
            ShopifyProviderInstallationProjector(
                db
            )
            .project_connected(
                user_id=user_id,
                connection_id=uuid4(),
                shop_domain=(
                    "example.myshopify.com"
                ),
                has_access_token=True,
            )
        )
        await db.commit()

        snapshot = await (
            DatabaseProviderInstallationReader(
                db
            )
            .get_provider_installation(
                user_id=user_id,
                tenant_id=None,
                provider_id="shopify",
            )
        )

        serialized = snapshot.model_dump(
            mode="json"
        )

        assert "access_token" not in serialized
        assert (
            "access_token_encrypted"
            not in serialized
        )
        assert (
            set(snapshot.metadata)
            == {"shop_domain"}
        )
