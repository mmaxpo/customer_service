from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.auth as auth_api
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


def signup_payload(email: str, password: str) -> dict[str, object]:
    return {
        "email": email,
        "password": password,
        **LEGAL_ACCEPTANCE,
    }


class AllowVerificationRateStore:
    async def increment(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        assert key.startswith("email-verification:")
        assert window_seconds == 60
        return 1


class RejectVerificationRateStore:
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
        return auth_api.EMAIL_VERIFICATION_RESEND_LIMIT_PER_MINUTE + 1


@pytest.mark.asyncio
async def test_unverified_user_is_blocked_from_workspace_access():
    email = f"unverified-workspace-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        signup = await client.post(
            "/auth/signup",
            json=signup_payload(email, password),
        )
        assert signup.status_code == 201

        login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )
        assert login.status_code == 200

        response = await client.get("/workspaces")

    assert response.status_code == 403
    assert response.json() == {"detail": {"code": "email_verification_required"}}


@pytest.mark.asyncio
async def test_unverified_user_can_use_me_and_resend(
    monkeypatch,
):
    email = f"unverified-recovery-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    sent_tokens: list[str] = []

    def fake_send_action_email(
        *,
        to: str,
        subject: str,
        path: str,
        token: str,
    ) -> None:
        assert to == email
        assert subject == "Verify your Tajeran email"
        assert path == "verify-email"
        sent_tokens.append(token)

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        fake_send_action_email,
    )
    monkeypatch.setattr(
        auth_api,
        "_verification_rate_store",
        AllowVerificationRateStore(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        assert (
            await client.post(
                "/auth/signup",
                json=signup_payload(email, password),
            )
        ).status_code == 201

        assert (
            await client.post(
                "/auth/login",
                json={"email": email, "password": password},
            )
        ).status_code == 200

        me = await client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["email_verified_at"] is None

        resend = await client.post(
            "/auth/email-verification/request",
        )
        assert resend.status_code == 202

    assert len(sent_tokens) == 1


@pytest.mark.asyncio
async def test_resend_invalidates_previous_verification_token(
    monkeypatch,
):
    email = f"verification-resend-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    sent_tokens: list[str] = []

    def fake_send_action_email(
        *,
        to: str,
        subject: str,
        path: str,
        token: str,
    ) -> None:
        sent_tokens.append(token)

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        fake_send_action_email,
    )
    monkeypatch.setattr(
        auth_api,
        "_verification_rate_store",
        AllowVerificationRateStore(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        assert (
            await client.post(
                "/auth/signup",
                json=signup_payload(email, password),
            )
        ).status_code == 201

        assert (
            await client.post(
                "/auth/login",
                json={"email": email, "password": password},
            )
        ).status_code == 200

        assert (
            await client.post("/auth/email-verification/request")
        ).status_code == 202

        assert (
            await client.post("/auth/email-verification/request")
        ).status_code == 202

        assert len(sent_tokens) == 2
        assert sent_tokens[0] != sent_tokens[1]

        old = await client.post(
            "/auth/email-verification/confirm",
            json={"token": sent_tokens[0]},
        )

        assert old.status_code == 400
        assert "Request a new verification email." in (old.json()["detail"])

        latest = await client.post(
            "/auth/email-verification/confirm",
            json={"token": sent_tokens[1]},
        )

        assert latest.status_code == 204

        workspace = await client.get("/workspaces")

    assert workspace.status_code == 200


@pytest.mark.asyncio
async def test_verification_resend_is_rate_limited(
    monkeypatch,
):
    email = f"verification-limit-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    store = RejectVerificationRateStore()

    monkeypatch.setattr(
        auth_api,
        "_verification_rate_store",
        store,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        assert (
            await client.post(
                "/auth/signup",
                json=signup_payload(email, password),
            )
        ).status_code == 201

        assert (
            await client.post(
                "/auth/login",
                json={"email": email, "password": password},
            )
        ).status_code == 200

        response = await client.post(
            "/auth/email-verification/request",
        )

    assert response.status_code == 429
    assert response.json() == {"detail": "Verification resend rate limit exceeded"}

    assert any(key.startswith("email-verification:user:") for key in store.keys)
    assert any(key.startswith("email-verification:email:") for key in store.keys)

    assert all(email not in key for key in store.keys)


@pytest.mark.asyncio
async def test_used_verification_token_has_recovery_instruction():
    email = f"verification-used-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        assert (
            await client.post(
                "/auth/signup",
                json=signup_payload(email, password),
            )
        ).status_code == 201

        async with SessionLocal() as session:
            user = await get_user_by_email(email, session)
            assert user is not None

            token = await create_action_token(
                session,
                user_id=user.id,
                kind="email_verification",
                expires_in=timedelta(minutes=5),
            )

        first = await client.post(
            "/auth/email-verification/confirm",
            json={"token": token},
        )
        assert first.status_code == 204

        replay = await client.post(
            "/auth/email-verification/confirm",
            json={"token": token},
        )

    assert replay.status_code == 400
    assert "Request a new verification email." in (replay.json()["detail"])
