from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.models.models import PlatformEvent
from app.api.auth import get_current_user
from app.domains.customer_service.services.shopify import (
    ShopifyService,
)
from app.domains.customer_service.services.shopify_provider_lifecycle import (
    ShopifyProviderLifecycleEvents,
)
from app.domains.customer_service.providers.shopify import (
    FakeShopifyProvider,
)
from sqlalchemy import select


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


class FailingVerificationProvider(
    FakeShopifyProvider
):
    async def verify_connection(
        self,
        *,
        shop_domain,
        access_token,
    ):
        raise RuntimeError(
            "revoked Shopify token"
        )


@pytest.mark.asyncio
async def test_generic_shopify_verification_marks_installation_verified():
    user_id = uuid4()

    async with SessionLocal() as db:
        await ShopifyService(
            db,
            provider=FakeShopifyProvider(),
        ).connect(
            user_id=user_id,
            shop_domain=(
                "verify-success.myshopify.com"
            ),
            access_token="test-token",
        )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/capabilities/"
                "provider-installations/"
                "shopify/verify"
            )

        assert response.status_code == 200

        body = response.json()

        assert body["provider_id"] == "shopify"
        assert body["ok"] is True
        assert (
            body["installation"]
            ["verification_state"]
            == "verified"
        )
        assert (
            body["installation"]
            ["authentication_state"]
            == "authenticated"
        )

        async with SessionLocal() as db:
            result = await db.execute(
                select(PlatformEvent).where(
                    PlatformEvent.user_id
                    == user_id,
                    PlatformEvent.event_type
                    == (
                        "runtime.provider."
                        "installation.verified"
                    ),
                )
            )

            events = list(
                result.scalars().all()
            )

        assert events
        assert (
            events[-1].payload[
                "provider_id"
            ]
            == "shopify"
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_shopify_failed_verification_projects_failure_event():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = ShopifyService(
            db,
            provider=(
                FailingVerificationProvider()
            ),
        )

        await service.connect(
            user_id=user_id,
            shop_domain=(
                "verify-failure.myshopify.com"
            ),
            access_token="revoked-token",
        )

        result = await service.test_connection(
            user_id=user_id,
        )

        assert result["ok"] is False

    async with SessionLocal() as db:
        result = await db.execute(
            select(PlatformEvent).where(
                PlatformEvent.user_id
                == user_id,
                PlatformEvent.event_type
                == (
                    "runtime.provider."
                    "installation."
                    "verification_failed"
                ),
            )
        )

        events = list(
            result.scalars().all()
        )

    assert events
    assert (
        events[-1].payload[
            "verification_state"
        ]
        == "failed"
    )
    assert (
        events[-1].payload[
            "authentication_state"
        ]
        == "invalid"
    )


@pytest.mark.asyncio
async def test_generic_verification_rejects_unknown_provider():
    user_id = uuid4()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/capabilities/"
                "provider-installations/"
                "unknown/verify"
            )

        assert response.status_code == 422
        assert (
            "not supported"
            in response.json()["detail"]
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_enabled_update_publishes_lifecycle_event():
    user_id = uuid4()

    async with SessionLocal() as db:
        await ShopifyService(
            db,
            provider=FakeShopifyProvider(),
        ).connect(
            user_id=user_id,
            shop_domain=(
                "disable-event.myshopify.com"
            ),
            access_token="test-token",
        )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/capabilities/"
                "provider-installations/"
                "shopify",
                json={
                    "tenant_id": None,
                    "enabled": False,
                },
            )

        assert response.status_code == 200

        async with SessionLocal() as db:
            result = await db.execute(
                select(PlatformEvent).where(
                    PlatformEvent.user_id
                    == user_id,
                    PlatformEvent.event_type
                    == (
                        "runtime.provider."
                        "installation.disabled"
                    ),
                )
            )

            events = list(
                result.scalars().all()
            )

        assert events
        assert (
            events[-1].payload["enabled"]
            is False
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_reenable_preserves_verification_state():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = ShopifyService(
            db,
            provider=FakeShopifyProvider(),
        )
        await service.connect(
            user_id=user_id,
            shop_domain=(
                "reenable.myshopify.com"
            ),
            access_token="test-token",
        )
        result = await service.test_connection(
            user_id=user_id,
        )
        assert result["ok"] is True

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            disabled = await client.patch(
                "/capabilities/"
                "provider-installations/"
                "shopify",
                json={
                    "tenant_id": None,
                    "enabled": False,
                },
            )
            assert disabled.status_code == 200
            assert (
                disabled.json()
                ["verification_state"]
                == "verified"
            )

            enabled = await client.patch(
                "/capabilities/"
                "provider-installations/"
                "shopify",
                json={
                    "tenant_id": None,
                    "enabled": True,
                },
            )

            assert enabled.status_code == 200
            assert enabled.json()["enabled"] is True
            assert (
                enabled.json()
                ["verification_state"]
                == "verified"
            )

        async with SessionLocal() as db:
            result = await db.execute(
                select(PlatformEvent).where(
                    PlatformEvent.user_id
                    == user_id,
                    PlatformEvent.event_type
                    == (
                        "runtime.provider."
                        "installation.enabled"
                    ),
                )
            )
            events = list(
                result.scalars().all()
            )

        assert events
        assert (
            events[-1].payload["enabled"]
            is True
        )
        assert (
            events[-1].payload[
                "verification_state"
            ]
            == "verified"
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_reconciliation_publishes_secret_free_event():
    user_id = uuid4()

    async with SessionLocal() as db:
        await ShopifyService(
            db,
            provider=FakeShopifyProvider(),
        ).connect(
            user_id=user_id,
            shop_domain=(
                "reconcile-event.myshopify.com"
            ),
            access_token="super-secret-token",
        )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/capabilities/"
                "provider-installations/"
                "reconcile/shopify"
            )

        assert response.status_code == 200

        async with SessionLocal() as db:
            result = await db.execute(
                select(PlatformEvent).where(
                    PlatformEvent.user_id
                    == user_id,
                    PlatformEvent.event_type
                    == (
                        "runtime.provider."
                        "installation.reconciled"
                    ),
                )
            )
            events = list(
                result.scalars().all()
            )

        assert events

        payload_text = str(
            events[-1].payload
        )

        assert (
            "super-secret-token"
            not in payload_text
        )
        assert (
            "access_token"
            not in payload_text
        )
        assert (
            events[-1].payload[
                "provider_id"
            ]
            == "shopify"
        )
        assert (
            events[-1].payload[
                "projected"
            ]
            == 1
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_provider_state_and_event_roll_back_together(
    monkeypatch,
):
    from app.domains.customer_service.services import (
        shopify_provider_lifecycle,
    )
    from app.runtime.capabilities.execution.installation.repository import (
        CapabilityProviderInstallationRepository,
    )

    user_id = uuid4()

    async with SessionLocal() as db:
        service = ShopifyService(
            db,
            provider=FakeShopifyProvider(),
        )
        await service.connect(
            user_id=user_id,
            shop_domain="atomic.myshopify.com",
            access_token="test-token",
        )
        await service.test_connection(
            user_id=user_id,
        )

    original_publish = (
        shopify_provider_lifecycle
        .PlatformEventPublisher
        .publish
    )

    async def failing_publish(
        self,
        **kwargs,
    ):
        await original_publish(
            self,
            **kwargs,
        )
        raise RuntimeError(
            "event lifecycle failure"
        )

    monkeypatch.setattr(
        shopify_provider_lifecycle
        .PlatformEventPublisher,
        "publish",
        failing_publish,
    )

    async with SessionLocal() as db:
        repo = CapabilityProviderInstallationRepository(
            db
        )
        row = await repo.set_enabled(
            user_id=user_id,
            tenant_id=None,
            provider_id="shopify",
            enabled=False,
        )

        assert row is not None

        with pytest.raises(
            RuntimeError,
            match="event lifecycle failure",
        ):
            await ShopifyProviderLifecycleEvents(
                db
            ).enabled_changed(
                user_id=user_id,
                installation=row,
            )

        await db.rollback()

    async with SessionLocal() as db:
        row = await (
            CapabilityProviderInstallationRepository(
                db
            )
            .get_exact(
                user_id=user_id,
                tenant_id=None,
                provider_id="shopify",
            )
        )

        assert row is not None
        assert row.enabled is True
