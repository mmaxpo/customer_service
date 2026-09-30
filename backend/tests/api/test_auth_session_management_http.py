from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.auth as auth_api
from app.identity import create_access_token, decode_identity_claims
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


async def _login(
    client: AsyncClient,
    monkeypatch,
    *,
    email: str,
    password: str,
    user_agent: str | None = None,
):
    monkeypatch.setattr(
        auth_api,
        "_login_failure_rate_store",
        AllowLoginFailureStore(),
    )

    headers = {}

    if user_agent is not None:
        headers["user-agent"] = user_agent

    return await client.post(
        "/auth/login",
        headers=headers,
        json={
            "email": email,
            "password": password,
        },
    )


def _bearer(access_token: str) -> dict[str, str]:
    return {
        "authorization": f"Bearer {access_token}",
    }


@pytest.mark.asyncio
async def test_sidless_access_token_is_rejected(
    monkeypatch,
):
    email = f"sidless-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

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

        login = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
        )
        assert login.status_code == 200

        normal_claims = decode_identity_claims(
            login.json()["access_token"],
            expected_type="access",
        )

        sidless = create_access_token(
            {
                "uid": normal_claims["uid"],
                "sub": normal_claims["sub"],
            },
            token_type="access",
        )

        response = await client.get(
            "/auth/me",
            headers=_bearer(sidless),
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"


@pytest.mark.asyncio
async def test_list_sessions_returns_only_safe_active_sessions_and_marks_current(
    monkeypatch,
):
    email = f"sessions-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

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

        first = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
            user_agent="Tajeran-Test-Device-One",
        )
        second = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
            user_agent="Tajeran-Test-Device-Two",
        )

        assert first.status_code == 200
        assert second.status_code == 200

        first_access = first.json()["access_token"]
        second_access = second.json()["access_token"]

        first_sid = str(
            decode_identity_claims(
                first_access,
                expected_type="access",
            )["sid"]
        )
        second_sid = str(
            decode_identity_claims(
                second_access,
                expected_type="access",
            )["sid"]
        )

        response = await client.get(
            "/auth/sessions",
            headers=_bearer(first_access),
        )

    assert response.status_code == 200

    rows = response.json()

    by_id = {row["id"]: row for row in rows}

    assert first_sid in by_id
    assert second_sid in by_id

    assert by_id[first_sid]["current"] is True
    assert by_id[second_sid]["current"] is False

    assert by_id[first_sid]["user_agent"] == "Tajeran-Test-Device-One"
    assert by_id[second_sid]["user_agent"] == "Tajeran-Test-Device-Two"

    allowed_keys = {
        "id",
        "current",
        "user_agent",
        "ip_address",
        "created_at",
        "last_used_at",
        "expires_at",
    }

    for row in rows:
        assert set(row) == allowed_keys
        assert "refresh_token_hash" not in row
        assert "family_id" not in row


@pytest.mark.asyncio
async def test_user_can_revoke_one_selected_owned_session(
    monkeypatch,
):
    email = f"revoke-one-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

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

        first = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
        )
        second = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
        )

        assert first.status_code == 200
        assert second.status_code == 200

        first_access = first.json()["access_token"]
        second_access = second.json()["access_token"]

        second_sid = str(
            decode_identity_claims(
                second_access,
                expected_type="access",
            )["sid"]
        )

        revoke = await client.delete(
            f"/auth/sessions/{second_sid}",
            headers=_bearer(first_access),
        )

        assert revoke.status_code == 204

        first_after = await client.get(
            "/auth/me",
            headers=_bearer(first_access),
        )
        second_after = await client.get(
            "/auth/me",
            headers=_bearer(second_access),
        )

    assert first_after.status_code == 200
    assert second_after.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_session_revocation_is_hidden_and_rejected(
    monkeypatch,
):
    password = f"Strong-Password-{uuid4()}!"
    first_email = f"session-owner-a-{uuid4()}@example.com"
    second_email = f"session-owner-b-{uuid4()}@example.com"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=first_email,
            password=password,
        )
        await _signup(
            client,
            monkeypatch,
            email=second_email,
            password=password,
        )

        first = await _login(
            client,
            monkeypatch,
            email=first_email,
            password=password,
        )
        second = await _login(
            client,
            monkeypatch,
            email=second_email,
            password=password,
        )

        assert first.status_code == 200
        assert second.status_code == 200

        first_access = first.json()["access_token"]
        second_access = second.json()["access_token"]

        second_sid = str(
            decode_identity_claims(
                second_access,
                expected_type="access",
            )["sid"]
        )

        attack = await client.delete(
            f"/auth/sessions/{second_sid}",
            headers=_bearer(first_access),
        )

        victim_after = await client.get(
            "/auth/me",
            headers=_bearer(second_access),
        )

    assert attack.status_code == 404
    assert attack.json() == {
        "detail": "Session not found",
    }
    assert victim_after.status_code == 200


@pytest.mark.asyncio
async def test_logout_others_preserves_current_session_and_revokes_other_sessions(
    monkeypatch,
):
    email = f"logout-others-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

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

        first = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
        )
        second = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
        )
        third = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 200

        first_access = first.json()["access_token"]
        second_access = second.json()["access_token"]
        third_access = third.json()["access_token"]

        response = await client.post(
            "/auth/sessions/logout-others",
            headers=_bearer(first_access),
        )

        assert response.status_code == 204

        first_after = await client.get(
            "/auth/me",
            headers=_bearer(first_access),
        )
        second_after = await client.get(
            "/auth/me",
            headers=_bearer(second_access),
        )
        third_after = await client.get(
            "/auth/me",
            headers=_bearer(third_access),
        )

        sessions_after = await client.get(
            "/auth/sessions",
            headers=_bearer(first_access),
        )

    assert first_after.status_code == 200
    assert second_after.status_code == 401
    assert third_after.status_code == 401

    assert sessions_after.status_code == 200
    rows = sessions_after.json()
    assert len(rows) == 1
    assert rows[0]["current"] is True


@pytest.mark.asyncio
async def test_logout_all_still_revokes_current_and_other_sessions(
    monkeypatch,
):
    email = f"logout-all-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

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

        first = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
        )
        second = await _login(
            client,
            monkeypatch,
            email=email,
            password=password,
        )

        assert first.status_code == 200
        assert second.status_code == 200

        first_access = first.json()["access_token"]
        second_access = second.json()["access_token"]

        logout_all = await client.post(
            "/auth/logout-all",
            headers=_bearer(first_access),
        )

        assert logout_all.status_code == 204

        first_after = await client.get(
            "/auth/me",
            headers=_bearer(first_access),
        )
        second_after = await client.get(
            "/auth/me",
            headers=_bearer(second_access),
        )

    assert first_after.status_code == 401
    assert second_after.status_code == 401
