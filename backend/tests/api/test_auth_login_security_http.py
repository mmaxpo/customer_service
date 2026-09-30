from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.api.auth as auth_api
from app.core.session import SessionLocal
from app.main import app
from app.models.models import PlatformEvent, User as UserORM


LEGAL_ACCEPTANCE = {
    "terms_accepted": True,
    "terms_version": "v1",
    "privacy_accepted": True,
    "privacy_version": "v1",
}


class AllowSignupRateStore:
    async def increment(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        assert key.startswith("signup:")
        assert window_seconds == 60
        return 1


class FakeLoginFailureStore:
    def __init__(self) -> None:
        self.counts: dict[str, int] = defaultdict(int)

    async def current(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        assert window_seconds == 60
        return self.counts[key]

    async def increment(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        assert window_seconds == 60
        self.counts[key] += 1
        return self.counts[key]

    async def reset(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> None:
        assert window_seconds == 60
        self.counts.pop(key, None)


async def _signup(
    client: AsyncClient,
    *,
    email: str,
    password: str,
) -> None:
    original_store = auth_api._signup_rate_store
    auth_api._signup_rate_store = AllowSignupRateStore()

    try:
        response = await client.post(
            "/auth/signup",
            json={
                "email": email,
                "password": password,
                **LEGAL_ACCEPTANCE,
            },
        )
    finally:
        auth_api._signup_rate_store = original_store

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_disabled_account_login_is_non_revealing(
    monkeypatch,
):
    email = f"disabled-login-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    monkeypatch.setattr(
        auth_api,
        "_login_failure_rate_store",
        FakeLoginFailureStore(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            email=email,
            password=password,
        )

        async with SessionLocal() as db:
            row = (
                await db.execute(
                    select(UserORM).where(UserORM.normalized_email == email)
                )
            ).scalar_one()

            row.is_active = False
            await db.commit()

        disabled = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        unknown = await client.post(
            "/auth/login",
            json={
                "email": f"unknown-{uuid4()}@example.com",
                "password": password,
            },
        )

    assert disabled.status_code == 401
    assert unknown.status_code == 401

    assert disabled.json() == {"detail": "Incorrect email or password"}
    assert unknown.json() == disabled.json()


@pytest.mark.asyncio
async def test_failed_login_backoff_blocks_after_limit(
    monkeypatch,
):
    store = FakeLoginFailureStore()

    monkeypatch.setattr(
        auth_api,
        "_login_failure_rate_store",
        store,
    )

    email = f"login-limit-{uuid4()}@example.com"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        statuses = []

        for _ in range(auth_api.LOGIN_FAILURE_LIMIT):
            response = await client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": "Wrong-Password-123!",
                },
            )
            statuses.append(response.status_code)

        blocked = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "Wrong-Password-123!",
            },
        )

    assert statuses[:-1] == [401] * (auth_api.LOGIN_FAILURE_LIMIT - 1)

    assert statuses[-1] == 429
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"


@pytest.mark.asyncio
async def test_successful_login_clears_failure_backoff(
    monkeypatch,
):
    store = FakeLoginFailureStore()

    monkeypatch.setattr(
        auth_api,
        "_login_failure_rate_store",
        store,
    )

    email = f"login-reset-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            email=email,
            password=password,
        )

        failed = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "Wrong-Password-123!",
            },
        )

        assert failed.status_code == 401
        assert store.counts

        success = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

    assert success.status_code == 200

    assert not any(
        value for key, value in store.counts.items() if key.startswith("login-failure:")
    )


@pytest.mark.asyncio
async def test_login_success_and_failure_are_recorded_without_secrets(
    monkeypatch,
):
    store = FakeLoginFailureStore()

    monkeypatch.setattr(
        auth_api,
        "_login_failure_rate_store",
        store,
    )

    email = f"login-audit-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            email=email,
            password=password,
        )

        failure = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "Wrong-Password-123!",
            },
        )
        assert failure.status_code == 401

        success = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )
        assert success.status_code == 200

    async with SessionLocal() as db:
        events = list(
            (
                await db.execute(
                    select(PlatformEvent)
                    .where(
                        PlatformEvent.event_type.in_(
                            (
                                "identity.login.failed",
                                "identity.login.succeeded",
                            )
                        )
                    )
                    .order_by(PlatformEvent.created_at.desc())
                )
            )
            .scalars()
            .all()
        )

    matched = [
        event
        for event in events
        if event.payload.get("email_digest")
        == auth_api._login_security_keys(
            type(
                "RequestStub",
                (),
                {
                    "client": type(
                        "ClientStub",
                        (),
                        {"host": "127.0.0.1"},
                    )()
                },
            )(),
            email=email,
        )[3]
    ]

    kinds = {event.event_type for event in matched}

    assert "identity.login.failed" in kinds
    assert "identity.login.succeeded" in kinds

    serialized = repr([event.payload for event in matched])

    assert email not in serialized
    assert password not in serialized
    assert "Wrong-Password-123!" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized


@pytest.mark.asyncio
async def test_successful_logins_create_distinct_session_ids(
    monkeypatch,
):
    monkeypatch.setattr(
        auth_api,
        "_login_failure_rate_store",
        FakeLoginFailureStore(),
    )

    email = f"session-id-login-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            email=email,
            password=password,
        )

        first = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )
        assert first.status_code == 200

        second = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )
        assert second.status_code == 200

    first_claims = auth_api.decode_identity_claims(first.json()["access_token"])
    second_claims = auth_api.decode_identity_claims(second.json()["access_token"])

    assert first_claims["sid"] != second_claims["sid"]
