from __future__ import annotations

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
):
    monkeypatch.setattr(
        auth_api,
        "_login_failure_rate_store",
        AllowLoginFailureStore(),
    )

    return await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )


@pytest.mark.asyncio
async def test_email_change_requires_authentication():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/email-change/request",
            json={
                "current_password": "Password-123!",
                "new_email": "new@example.com",
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_email_change_requires_current_password_and_keeps_old_email_until_confirm(
    monkeypatch,
):
    old_email = f"old-{uuid4()}@example.com"
    new_email = f"NEW-{uuid4()}@Example.COM"
    canonical_new = new_email.casefold()
    password = f"Strong-Password-{uuid4()}!"

    action_emails: list[dict] = []
    security_emails: list[dict] = []

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: action_emails.append(kwargs),
    )
    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: security_emails.append(kwargs),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        login = await _login(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        assert login.status_code == 200

        headers = {"authorization": (f"Bearer {login.json()['access_token']}")}

        wrong = await client.post(
            "/auth/email-change/request",
            headers=headers,
            json={
                "current_password": "Wrong-Password-123!",
                "new_email": new_email,
            },
        )

        assert wrong.status_code == 400
        assert action_emails == []
        assert security_emails == []

        requested = await client.post(
            "/auth/email-change/request",
            headers=headers,
            json={
                "current_password": password,
                "new_email": new_email,
            },
        )

        assert requested.status_code == 202

    async with SessionLocal() as db:
        row = await db.scalar(
            select(UserORM).where(UserORM.normalized_email == old_email.casefold())
        )

    assert row is not None
    assert row.email == old_email.casefold()
    assert row.normalized_email == old_email.casefold()

    assert len(action_emails) == 1
    assert action_emails[0]["to"] == canonical_new
    assert action_emails[0]["token"]

    assert len(security_emails) == 1
    assert security_emails[0]["to"] == old_email.casefold()


@pytest.mark.asyncio
async def test_email_change_rejects_existing_and_same_email(
    monkeypatch,
):
    first_email = f"first-{uuid4()}@example.com"
    second_email = f"second-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: None,
    )

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

        login = await _login(
            client,
            monkeypatch,
            email=first_email,
            password=password,
        )

        assert login.status_code == 200

        headers = {"authorization": (f"Bearer {login.json()['access_token']}")}

        duplicate = await client.post(
            "/auth/email-change/request",
            headers=headers,
            json={
                "current_password": password,
                "new_email": second_email.upper(),
            },
        )

        same = await client.post(
            "/auth/email-change/request",
            headers=headers,
            json={
                "current_password": password,
                "new_email": first_email.upper(),
            },
        )

    assert duplicate.status_code == 409
    assert same.status_code == 400


@pytest.mark.asyncio
async def test_new_email_change_request_invalidates_previous_token(
    monkeypatch,
):
    old_email = f"replace-{uuid4()}@example.com"
    first_new = f"first-new-{uuid4()}@example.com"
    second_new = f"second-new-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    tokens: list[str] = []

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: tokens.append(kwargs["token"]),
    )
    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: None,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        login = await _login(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        assert login.status_code == 200

        headers = {"authorization": (f"Bearer {login.json()['access_token']}")}

        first = await client.post(
            "/auth/email-change/request",
            headers=headers,
            json={
                "current_password": password,
                "new_email": first_new,
            },
        )

        second = await client.post(
            "/auth/email-change/request",
            headers=headers,
            json={
                "current_password": password,
                "new_email": second_new,
            },
        )

        assert first.status_code == 202
        assert second.status_code == 202
        assert len(tokens) == 2
        assert tokens[0] != tokens[1]

        stale = await client.post(
            "/auth/email-change/confirm",
            json={"token": tokens[0]},
        )

    assert stale.status_code == 400


@pytest.mark.asyncio
async def test_email_change_confirm_updates_identity_revokes_sessions_and_notifies(
    monkeypatch,
):
    old_email = f"confirm-old-{uuid4()}@example.com"
    new_email = f"CONFIRM-NEW-{uuid4()}@Example.COM"
    canonical_new = new_email.casefold()
    password = f"Strong-Password-{uuid4()}!"

    tokens: list[str] = []
    security_emails: list[dict] = []

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: tokens.append(kwargs["token"]),
    )
    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: security_emails.append(kwargs),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        login = await _login(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        assert login.status_code == 200
        old_access = login.json()["access_token"]

        requested = await client.post(
            "/auth/email-change/request",
            headers={"authorization": f"Bearer {old_access}"},
            json={
                "current_password": password,
                "new_email": new_email,
            },
        )

        assert requested.status_code == 202
        assert len(tokens) == 1

        confirmed = await client.post(
            "/auth/email-change/confirm",
            json={"token": tokens[0]},
        )

        assert confirmed.status_code == 204

        replay = await client.post(
            "/auth/email-change/confirm",
            json={"token": tokens[0]},
        )

        assert replay.status_code == 400

        old_session = await client.get(
            "/auth/me",
            headers={"authorization": f"Bearer {old_access}"},
        )

        assert old_session.status_code == 401

        old_login = await _login(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        assert old_login.status_code == 401

        new_login = await _login(
            client,
            monkeypatch,
            email=canonical_new,
            password=password,
        )

        assert new_login.status_code == 200

    async with SessionLocal() as db:
        row = await db.scalar(
            select(UserORM).where(UserORM.normalized_email == canonical_new)
        )

    assert row is not None
    assert row.email == canonical_new
    assert row.normalized_email == canonical_new
    assert row.email_verified_at is not None

    destinations = [item["to"] for item in security_emails]

    # Request notification to old address.
    assert old_email.casefold() in destinations

    # Confirmation notification to new address.
    assert canonical_new in destinations


@pytest.mark.asyncio
async def test_email_change_confirm_rechecks_uniqueness_and_burns_conflicting_token(
    monkeypatch,
):
    old_email = f"race-old-{uuid4()}@example.com"
    target_email = f"race-target-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    tokens: list[str] = []

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: tokens.append(kwargs["token"]),
    )
    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: None,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        login = await _login(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        assert login.status_code == 200

        requested = await client.post(
            "/auth/email-change/request",
            headers={"authorization": (f"Bearer {login.json()['access_token']}")},
            json={
                "current_password": password,
                "new_email": target_email,
            },
        )

        assert requested.status_code == 202
        assert len(tokens) == 1

        # Another account claims the address after the request.
        await _signup(
            client,
            monkeypatch,
            email=target_email,
            password=password,
        )

        conflict = await client.post(
            "/auth/email-change/confirm",
            json={"token": tokens[0]},
        )

        assert conflict.status_code == 409

        replay = await client.post(
            "/auth/email-change/confirm",
            json={"token": tokens[0]},
        )

        assert replay.status_code == 400

    async with SessionLocal() as db:
        original = await db.scalar(
            select(UserORM).where(UserORM.normalized_email == old_email.casefold())
        )

    assert original is not None
    assert original.email == old_email.casefold()


@pytest.mark.asyncio
async def test_email_change_audit_events_do_not_store_raw_email_or_token(
    monkeypatch,
):
    old_email = f"audit-old-{uuid4()}@example.com"
    new_email = f"audit-new-{uuid4()}@example.com"
    password = f"Strong-Password-{uuid4()}!"

    tokens: list[str] = []

    monkeypatch.setattr(
        auth_api,
        "_send_action_email",
        lambda **kwargs: tokens.append(kwargs["token"]),
    )
    monkeypatch.setattr(
        auth_api,
        "_send_security_notification",
        lambda **kwargs: None,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await _signup(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        login = await _login(
            client,
            monkeypatch,
            email=old_email,
            password=password,
        )

        assert login.status_code == 200

        requested = await client.post(
            "/auth/email-change/request",
            headers={"authorization": (f"Bearer {login.json()['access_token']}")},
            json={
                "current_password": password,
                "new_email": new_email,
            },
        )

        assert requested.status_code == 202
        assert len(tokens) == 1

        confirmed = await client.post(
            "/auth/email-change/confirm",
            json={"token": tokens[0]},
        )

        assert confirmed.status_code == 204

    async with SessionLocal() as db:
        events = list(
            (
                await db.execute(
                    select(PlatformEvent).where(
                        PlatformEvent.event_type.in_(
                            (
                                "identity.email_change.requested",
                                "identity.email_change.confirmed",
                            )
                        )
                    )
                )
            )
            .scalars()
            .all()
        )

    assert events

    serialized = repr(
        [
            {
                "event_type": event.event_type,
                "payload": event.payload,
            }
            for event in events
        ]
    )

    assert old_email not in serialized
    assert new_email not in serialized
    assert tokens[0] not in serialized

    kinds = {event.event_type for event in events}

    assert "identity.email_change.requested" in kinds
    assert "identity.email_change.confirmed" in kinds
