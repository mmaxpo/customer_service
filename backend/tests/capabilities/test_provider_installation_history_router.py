from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.platform.events.publisher import (
    PlatformEventPublisher,
)
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


async def publish_installation_event(
    *,
    user_id,
    provider_id: str,
    event_type: str,
    installation_id=None,
    tenant_id=None,
    version: int | None = None,
    secret: str | None = None,
):
    async with SessionLocal() as db:
        payload = {
            "provider_id": provider_id,
            "installation_id": (
                str(installation_id)
                if installation_id is not None
                else None
            ),
            "tenant_id": tenant_id,
            "integration_kind": provider_id,
            "integration_connection_id": (
                "connection_1"
            ),
            "enabled": True,
            "configuration_state": "configured",
            "authentication_state": (
                "authenticated"
            ),
            "verification_state": (
                "verified"
                if event_type.endswith(
                    ".verified"
                )
                else "unverified"
            ),
            "failure_code": (
                "verification_failed"
                if event_type.endswith(
                    "verification_failed"
                )
                else None
            ),
            "version": version,
            "shop": {
                "id": "shop_1",
                "name": "History Shop",
                "myshopify_domain": (
                    "history.myshopify.com"
                ),
            },
        }

        if secret is not None:
            # The history API must expose only its explicit
            # allowlisted projection, never arbitrary payload
            # keys from old or malformed events.
            payload["access_token"] = secret

        await PlatformEventPublisher(
            db
        ).publish(
            user_id=user_id,
            event_type=event_type,
            source=(
                "runtime.provider_installations"
            ),
            payload=payload,
            dispatch=False,
        )


@pytest.mark.asyncio
async def test_provider_installation_history_is_user_and_provider_scoped():
    owner_id = uuid4()
    other_user_id = uuid4()
    installation_id = uuid4()

    await publish_installation_event(
        user_id=owner_id,
        provider_id="shopify",
        event_type=(
            "runtime.provider.installation."
            "verified"
        ),
        installation_id=installation_id,
        version=3,
    )
    await publish_installation_event(
        user_id=owner_id,
        provider_id="stripe",
        event_type=(
            "runtime.provider.installation."
            "verified"
        ),
        installation_id=uuid4(),
        version=1,
    )
    await publish_installation_event(
        user_id=other_user_id,
        provider_id="shopify",
        event_type=(
            "runtime.provider.installation."
            "verified"
        ),
        installation_id=uuid4(),
        version=9,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(owner_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "provider-installations/"
                "shopify/events"
            )

        assert response.status_code == 200

        body = response.json()

        assert body["provider_id"] == "shopify"
        assert len(body["items"]) == 1

        item = body["items"][0]

        assert (
            item["installation_id"]
            == str(installation_id)
        )
        assert (
            item["installation_version"]
            == 3
        )
        assert (
            item["event_type"]
            == (
                "runtime.provider."
                "installation.verified"
            )
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_provider_installation_history_filters_outcome_and_tenant():
    user_id = uuid4()
    tenant_id = f"tenant-history-{uuid4()}"

    await publish_installation_event(
        user_id=user_id,
        provider_id="shopify",
        event_type=(
            "runtime.provider.installation."
            "verified"
        ),
        installation_id=uuid4(),
        tenant_id=tenant_id,
        version=2,
    )
    await publish_installation_event(
        user_id=user_id,
        provider_id="shopify",
        event_type=(
            "runtime.provider.installation."
            "verification_failed"
        ),
        installation_id=uuid4(),
        tenant_id=tenant_id,
        version=3,
    )
    await publish_installation_event(
        user_id=user_id,
        provider_id="shopify",
        event_type=(
            "runtime.provider.installation."
            "verified"
        ),
        installation_id=uuid4(),
        tenant_id="other-tenant",
        version=4,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "provider-installations/"
                "shopify/events",
                params={
                    "tenant_id": tenant_id,
                    "outcome": "failed",
                },
            )

        assert response.status_code == 200

        items = response.json()["items"]

        assert len(items) == 1
        assert (
            items[0]["event_type"]
            == (
                "runtime.provider."
                "installation."
                "verification_failed"
            )
        )
        assert (
            items[0]["tenant_id"]
            == tenant_id
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_provider_installation_history_is_secret_free():
    user_id = uuid4()
    secret = "should-never-be-returned"

    await publish_installation_event(
        user_id=user_id,
        provider_id="shopify",
        event_type=(
            "runtime.provider.installation."
            "verified"
        ),
        installation_id=uuid4(),
        version=1,
        secret=secret,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "provider-installations/"
                "shopify/events"
            )

        assert response.status_code == 200

        serialized = str(response.json())

        assert secret not in serialized
        assert "access_token" not in serialized
        assert "payload" not in response.json()[
            "items"
        ][0]
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_provider_installation_history_paginates():
    user_id = uuid4()

    for version in range(1, 4):
        await publish_installation_event(
            user_id=user_id,
            provider_id="shopify",
            event_type=(
                "runtime.provider.installation."
                "enabled"
            ),
            installation_id=uuid4(),
            version=version,
        )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.get(
                "/capabilities/"
                "provider-installations/"
                "shopify/events",
                params={
                    "limit": 2,
                    "offset": 0,
                },
            )
            second = await client.get(
                "/capabilities/"
                "provider-installations/"
                "shopify/events",
                params={
                    "limit": 2,
                    "offset": 2,
                },
            )

        assert first.status_code == 200
        assert second.status_code == 200

        first_items = first.json()["items"]
        second_items = second.json()["items"]

        assert len(first_items) == 2
        assert len(second_items) == 1

        first_ids = {
            item["id"]
            for item in first_items
        }
        second_ids = {
            item["id"]
            for item in second_items
        }

        assert first_ids.isdisjoint(second_ids)
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_provider_installation_history_rejects_unknown_event_type():
    user_id = uuid4()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "provider-installations/"
                "shopify/events",
                params={
                    "event_type": (
                        "runtime.provider."
                        "installation.secret_dump"
                    ),
                },
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
