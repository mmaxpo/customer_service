from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.api.auth import get_current_user
from app.domains.customer_service.models import (
    CustomerServiceShopifyConnection,
)
from app.runtime.capabilities.execution.installation.models import (
    ProviderInstallationScope,
    ProviderInstallationUpsert,
)
from app.runtime.capabilities.execution.installation.repository import (
    CapabilityProviderInstallationRepository,
)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


@pytest.mark.asyncio
async def test_provider_installation_reads_and_update_are_user_scoped():
    first_user = uuid4()
    second_user = uuid4()

    async with SessionLocal() as db:
        await (
            CapabilityProviderInstallationRepository(
                db
            )
            .upsert(
                scope=ProviderInstallationScope(
                    user_id=first_user,
                    tenant_id=None,
                    provider_id="shopify",
                ),
                installation=(
                    ProviderInstallationUpsert(
                        integration_kind="shopify",
                    )
                ),
            )
        )
        await db.commit()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(first_user)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            listed = await client.get(
                "/capabilities/provider-installations"
            )

            assert listed.status_code == 200
            assert len(
                listed.json()["items"]
            ) == 1

            fetched = await client.get(
                "/capabilities/provider-installations/shopify"
            )

            assert fetched.status_code == 200
            assert (
                fetched.json()["provider_id"]
                == "shopify"
            )

            updated = await client.patch(
                "/capabilities/provider-installations/shopify",
                json={
                    "tenant_id": None,
                    "enabled": False,
                },
            )

            assert updated.status_code == 200
            assert (
                updated.json()["enabled"]
                is False
            )
            assert (
                updated.json()["version"]
                == 2
            )

            app.dependency_overrides[
                get_current_user
            ] = lambda: FakeUser(second_user)

            hidden = await client.get(
                "/capabilities/provider-installations"
            )
            assert hidden.status_code == 200
            assert (
                hidden.json()["items"]
                == []
            )

            hidden_item = await client.get(
                "/capabilities/provider-installations/shopify"
            )
            assert (
                hidden_item.status_code
                == 404
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_shopify_reconciliation_backfills_legacy_connection():
    user_id = uuid4()
    connection_id = uuid4()

    async with SessionLocal() as db:
        db.add(
            CustomerServiceShopifyConnection(
                id=connection_id,
                user_id=user_id,
                shop_domain=(
                    "legacy.myshopify.com"
                ),
                access_token_encrypted=(
                    "plain:legacy-token"
                ),
                status="active",
            )
        )
        await db.commit()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/capabilities/provider-installations/reconcile/shopify"
            )

            assert response.status_code == 200
            body = response.json()

            assert body["provider_id"] == "shopify"
            assert body["discovered"] == 1
            assert body["projected"] == 1

            item = body["items"][0]

            assert (
                item[
                    "integration_connection_id"
                ]
                == str(connection_id)
            )
            assert (
                item["configuration_state"]
                == "configured"
            )
            assert (
                item["authentication_state"]
                == "authenticated"
            )
            assert (
                item["verification_state"]
                == "unverified"
            )
            assert (
                item["metadata_json"]
                ["shop_domain"]
                == "legacy.myshopify.com"
            )

            serialized = str(item)

            assert "legacy-token" not in serialized
            assert "access_token" not in serialized
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_reconciliation_does_not_expose_other_users_connections():
    owner_id = uuid4()
    caller_id = uuid4()

    async with SessionLocal() as db:
        db.add(
            CustomerServiceShopifyConnection(
                user_id=owner_id,
                shop_domain=(
                    "private.myshopify.com"
                ),
                access_token_encrypted=(
                    "plain:private-token"
                ),
                status="active",
            )
        )
        await db.commit()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(caller_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/capabilities/provider-installations/reconcile/shopify"
            )

            assert response.status_code == 200
            assert (
                response.json()["discovered"]
                == 0
            )
            assert (
                response.json()["items"]
                == []
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_shopify_reconciliation_is_idempotent_by_scope():
    user_id = uuid4()
    connection_id = uuid4()

    async with SessionLocal() as db:
        db.add(
            CustomerServiceShopifyConnection(
                id=connection_id,
                user_id=user_id,
                shop_domain=(
                    "repeat.myshopify.com"
                ),
                access_token_encrypted=(
                    "plain:repeat-token"
                ),
                status="active",
            )
        )
        await db.commit()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/capabilities/provider-installations/reconcile/shopify"
            )
            second = await client.post(
                "/capabilities/provider-installations/reconcile/shopify"
            )

            assert first.status_code == 200
            assert second.status_code == 200

            first_item = first.json()["items"][0]
            second_item = second.json()["items"][0]

            assert first_item["id"] == second_item["id"]
            assert first_item["version"] == 1
            assert second_item["version"] == 2

            listed = await client.get(
                "/capabilities/provider-installations",
                params={
                    "provider_id": "shopify",
                },
            )

            assert listed.status_code == 200
            assert len(
                listed.json()["items"]
            ) == 1
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
