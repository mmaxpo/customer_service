from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.auth as auth_api

from app.api.auth import REFRESH_COOKIE
from app.authentication.service import create_action_token
from app.core.session import SessionLocal
from app.identity import get_user_by_email
from app.main import app


LEGAL_ACCEPTANCE = {
    "terms_accepted": True,
    "terms_version": "v1",
    "privacy_accepted": True,
    "privacy_version": "v1",
}


async def _signup_and_login(client: AsyncClient) -> dict[str, str]:
    email = f"auth-session-{uuid4()}@example.com"
    password = f"Session-{uuid4()}"
    signup = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            **LEGAL_ACCEPTANCE,
        },
    )
    assert signup.status_code == 201
    login = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


@pytest.mark.asyncio
async def test_refresh_rotates_and_reuse_revokes_session_family():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        first = await _signup_and_login(client)
        old_refresh = first["refresh_token"]

        refreshed = await client.post("/auth/refresh")
        assert refreshed.status_code == 200
        second = refreshed.json()
        assert second["refresh_token"] != old_refresh

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as replay_client:
            replay_client.cookies.set(REFRESH_COOKIE, old_refresh)
            replay = await replay_client.post("/auth/refresh")
            assert replay.status_code == 401

        after_reuse = await client.get(
            "/auth/me",
            headers={
                "authorization": f"Bearer {second['access_token']}",
            },
        )
        assert after_reuse.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_server_session():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        tokens = await _signup_and_login(client)

        logout = await client.post("/auth/logout")
        assert logout.status_code == 204

        after_logout = await client.get(
            "/auth/me",
            headers={
                "authorization": f"Bearer {tokens['access_token']}",
            },
        )
        assert after_logout.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_token_is_single_use_and_revokes_sessions(
    monkeypatch,
):
    email = f"password-reset-{uuid4()}@example.com"
    old_password = f"Old-Password-{uuid4()}"
    new_password = f"New-Password-{uuid4()}"

    notifications: list[dict[str, str]] = []

    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: notifications.append(kwargs),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        signup = await client.post(
            "/auth/signup",
            json={
                "email": email,
                "password": old_password,
                **LEGAL_ACCEPTANCE,
            },
        )
        assert signup.status_code == 201
        login = await client.post(
            "/auth/login",
            json={"email": email, "password": old_password},
        )
        assert login.status_code == 200
        old_access = login.json()["access_token"]

        async with SessionLocal() as session:
            user = await get_user_by_email(email, session)
            assert user is not None
            reset_token = await create_action_token(
                session,
                user_id=user.id,
                kind="password_reset",
                expires_in=timedelta(minutes=5),
            )

        confirmed = await client.post(
            "/auth/password-reset/confirm",
            json={"token": reset_token, "new_password": new_password},
        )
        assert confirmed.status_code == 204

        replay = await client.post(
            "/auth/password-reset/confirm",
            json={"token": reset_token, "new_password": new_password},
        )
        assert replay.status_code == 400

        invalidated = await client.get(
            "/auth/me",
            headers={"authorization": f"Bearer {old_access}"},
        )
        assert invalidated.status_code == 401

        old_login = await client.post(
            "/auth/login",
            json={"email": email, "password": old_password},
        )
        assert old_login.status_code == 401
        new_login = await client.post(
            "/auth/login",
            json={"email": email, "password": new_password},
        )
        assert new_login.status_code == 200

    assert len(notifications) == 1
    assert notifications[0]["to"] == email
    assert notifications[0]["subject"] == "Your Tajeran password was reset"


@pytest.mark.asyncio
async def test_email_verification_token_is_single_use():
    email = f"email-verify-{uuid4()}@example.com"
    password = f"Verify-Password-{uuid4()}"
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        signup = await client.post(
            "/auth/signup",
            json={
                "email": email,
                "password": password,
                **LEGAL_ACCEPTANCE,
            },
        )
        assert signup.status_code == 201

        async with SessionLocal() as session:
            user = await get_user_by_email(email, session)
            assert user is not None
            verification_token = await create_action_token(
                session,
                user_id=user.id,
                kind="email_verification",
                expires_in=timedelta(minutes=5),
            )

        confirmed = await client.post(
            "/auth/email-verification/confirm",
            json={"token": verification_token},
        )
        assert confirmed.status_code == 204
        replay = await client.post(
            "/auth/email-verification/confirm",
            json={"token": verification_token},
        )
        assert replay.status_code == 400


@pytest.mark.asyncio
async def test_general_email_send_rejects_unauthenticated_callers():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/email/send",
            json={
                "type": "noreply",
                "to": "victim@example.com",
                "subject": "unsafe",
                "html": "<p>unsafe</p>",
            },
        )
    assert response.status_code == 401
