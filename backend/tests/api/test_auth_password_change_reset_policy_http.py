from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.auth as auth_api
from app.main import app


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
        return 1


class AllowLoginFailureStore:
    async def current(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        return 0

    async def increment(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        return 1

    async def reset(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> None:
        return None


class AllowPasswordResetRateStore:
    async def increment(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        assert key.startswith("password-reset:")
        assert window_seconds == 60
        return 1


class RejectPasswordResetRateStore:
    def __init__(self) -> None:
        self.keys: list[str] = []

    async def increment(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        self.keys.append(key)
        assert window_seconds == 60
        return auth_api.PASSWORD_RESET_REQUEST_LIMIT_PER_MINUTE + 1


async def _signup(
    client: AsyncClient,
    monkeypatch,
    *,
    email: str,
    password: str,
) -> None:
    monkeypatch.setattr(
        auth_api,
        "_signup_rate_store",
        AllowSignupRateStore(),
    )

    response = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            **LEGAL_ACCEPTANCE,
        },
    )

    assert response.status_code == 201


def _allow_login(monkeypatch) -> None:
    monkeypatch.setattr(
        auth_api,
        "_login_failure_rate_store",
        AllowLoginFailureStore(),
    )


@pytest.mark.asyncio
async def test_password_change_requires_authentication():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/password-change",
            json={
                "current_password": "Old-Password-123!",
                "new_password": "New-Password-123!",
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_password_change_requires_current_password_and_notifies(
    monkeypatch,
):
    email = f"password-change-{uuid4()}@example.com"
    old_password = f"Old-Password-{uuid4()}!"
    new_password = f"New-Password-{uuid4()}!"

    _allow_login(monkeypatch)

    sent: list[dict[str, str]] = []

    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: sent.append(kwargs),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=email,
            password=old_password,
        )

        login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": old_password,
            },
        )
        assert login.status_code == 200

        headers = {"authorization": (f"Bearer {login.json()['access_token']}")}

        wrong = await client.post(
            "/auth/password-change",
            headers=headers,
            json={
                "current_password": "Wrong-Password-123!",
                "new_password": new_password,
            },
        )

        assert wrong.status_code == 400
        assert sent == []

        changed = await client.post(
            "/auth/password-change",
            headers=headers,
            json={
                "current_password": old_password,
                "new_password": new_password,
            },
        )

        assert changed.status_code == 204

        old_login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": old_password,
            },
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": new_password,
            },
        )
        assert new_login.status_code == 200

    assert len(sent) == 1
    assert sent[0]["to"] == email
    assert sent[0]["subject"] == "Your Tajeran password was changed"


@pytest.mark.asyncio
async def test_password_change_enforces_shared_policy(
    monkeypatch,
):
    email = f"password-change-policy-{uuid4()}@example.com"
    password = "Original-Password-123!"

    _allow_login(monkeypatch)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=email,
            password=password,
        )

        login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )
        assert login.status_code == 200

        response = await client.post(
            "/auth/password-change",
            headers={"authorization": (f"Bearer {login.json()['access_token']}")},
            json={
                "current_password": password,
                # Long enough, but the policy also needs a number.
                "new_password": "onlylettersnonumber",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reset_request_response_privacy(
    monkeypatch,
):
    email = f"reset-privacy-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    monkeypatch.setattr(
        auth_api,
        "_password_reset_rate_store",
        AllowPasswordResetRateStore(),
    )

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: None,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=email,
            password=password,
        )

        existing = await client.post(
            "/auth/password-reset/request",
            json={"email": email},
        )

        unknown = await client.post(
            "/auth/password-reset/request",
            json={"email": f"unknown-{uuid4()}@example.com"},
        )

    assert existing.status_code == 202
    assert unknown.status_code == 202
    assert existing.json() == unknown.json()


@pytest.mark.asyncio
async def test_reset_request_has_hashed_dedicated_limit(
    monkeypatch,
):
    raw_email = f"Rate-Limit-{uuid4()}@Example.COM"
    store = RejectPasswordResetRateStore()

    monkeypatch.setattr(
        auth_api,
        "_password_reset_rate_store",
        store,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/password-reset/request",
            json={"email": raw_email},
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"

    assert len(store.keys) == 2

    assert all(key.startswith("password-reset:") for key in store.keys)

    assert all(
        raw_email not in key and raw_email.casefold() not in key for key in store.keys
    )


@pytest.mark.asyncio
async def test_new_reset_invalidates_old_revokes_sessions_and_notifies(
    monkeypatch,
):
    email = f"reset-reissue-{uuid4()}@example.com"
    old_password = f"Old-Password-{uuid4()}!"
    new_password = f"New-Password-{uuid4()}!"

    monkeypatch.setattr(
        auth_api,
        "_password_reset_rate_store",
        AllowPasswordResetRateStore(),
    )

    _allow_login(monkeypatch)

    reset_tokens: list[str] = []
    notifications: list[dict[str, str]] = []

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: reset_tokens.append(kwargs["token"]),
    )

    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: notifications.append(kwargs),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=email,
            password=old_password,
        )

        login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": old_password,
            },
        )
        assert login.status_code == 200

        old_access = login.json()["access_token"]

        first = await client.post(
            "/auth/password-reset/request",
            json={"email": email},
        )

        second = await client.post(
            "/auth/password-reset/request",
            json={"email": email},
        )

        assert first.status_code == 202
        assert second.status_code == 202

        assert len(reset_tokens) == 2
        assert reset_tokens[0] != reset_tokens[1]

        stale = await client.post(
            "/auth/password-reset/confirm",
            json={
                "token": reset_tokens[0],
                "new_password": new_password,
            },
        )
        assert stale.status_code == 400

        confirmed = await client.post(
            "/auth/password-reset/confirm",
            json={
                "token": reset_tokens[1],
                "new_password": new_password,
            },
        )

        assert confirmed.status_code == 204

        old_session = await client.get(
            "/auth/me",
            headers={"authorization": f"Bearer {old_access}"},
        )
        assert old_session.status_code == 401

        old_login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": old_password,
            },
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": new_password,
            },
        )
        assert new_login.status_code == 200

    assert len(notifications) == 1
    assert notifications[0]["to"] == email
    assert notifications[0]["subject"] == "Your Tajeran password was reset"
    assert "signed out" in notifications[0]["message"]


@pytest.mark.asyncio
async def test_reused_reset_token_does_not_notify_twice(
    monkeypatch,
):
    email = f"reset-replay-{uuid4()}@example.com"
    password = f"Old-Password-{uuid4()}!"
    new_password = f"New-Password-{uuid4()}!"

    monkeypatch.setattr(
        auth_api,
        "_password_reset_rate_store",
        AllowPasswordResetRateStore(),
    )

    tokens: list[str] = []
    notifications: list[dict[str, str]] = []

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: tokens.append(kwargs["token"]),
    )

    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: notifications.append(kwargs),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=email,
            password=password,
        )

        requested = await client.post(
            "/auth/password-reset/request",
            json={"email": email},
        )
        assert requested.status_code == 202

        first = await client.post(
            "/auth/password-reset/confirm",
            json={
                "token": tokens[0],
                "new_password": new_password,
            },
        )
        assert first.status_code == 204

        replay = await client.post(
            "/auth/password-reset/confirm",
            json={
                "token": tokens[0],
                "new_password": new_password,
            },
        )
        assert replay.status_code == 400

    assert len(notifications) == 1
