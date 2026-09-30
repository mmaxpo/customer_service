from __future__ import annotations

import hashlib
from collections import defaultdict
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

import app.api.auth as auth_api
from app.core.config import settings
from app.core.session import SessionLocal
from app.main import app
from app.models.models import User


LEGAL_ACCEPTANCE = {
    "terms_accepted": True,
    "terms_version": "v1",
    "privacy_accepted": True,
    "privacy_version": "v1",
}


def signup_payload(email: str) -> dict[str, object]:
    return {
        "email": email,
        "password": "Strong-Password-123!",
        **LEGAL_ACCEPTANCE,
    }


@pytest.mark.asyncio
async def test_duplicate_signup_has_same_status_and_body_as_new_signup():
    email = f"duplicate-private-{uuid4()}@example.com"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        first = await client.post(
            "/auth/signup",
            json=signup_payload(email),
        )
        duplicate = await client.post(
            "/auth/signup",
            json=signup_payload(email.upper()),
        )

    assert first.status_code == 201
    assert duplicate.status_code == first.status_code

    assert first.json() == {"detail": "Registration request accepted."}
    assert duplicate.json() == first.json()

    async with SessionLocal() as session:
        result = await session.execute(
            select(func.count()).select_from(User).where(User.normalized_email == email)
        )

        assert result.scalar_one() == 1


class ControlledRateStore:
    def __init__(
        self,
        *,
        reject_bucket: str,
        limit: int,
    ) -> None:
        self.reject_bucket = reject_bucket
        self.limit = limit
        self.keys: list[str] = []

    async def increment(
        self,
        key: str,
        *,
        window_seconds: int = 60,
    ) -> int:
        assert window_seconds == 60
        self.keys.append(key)

        if key.startswith(self.reject_bucket):
            return self.limit + 1

        return 1


@pytest.mark.asyncio
async def test_signup_rate_limit_rejects_by_ip(monkeypatch):
    limit = settings.RATE_LIMIT_AUTH_PER_MINUTE

    store = ControlledRateStore(
        reject_bucket="signup:ip:",
        limit=limit,
    )

    monkeypatch.setattr(
        auth_api,
        "_signup_rate_store",
        store,
    )

    email = f"rate-ip-{uuid4()}@example.com"

    transport = ASGITransport(
        app=app,
        client=("203.0.113.10", 12345),
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/signup",
            json=signup_payload(email),
        )

    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}

    expected_ip = hashlib.sha256(b"203.0.113.10").hexdigest()[:24]

    assert store.keys[0] == f"signup:ip:{expected_ip}"


@pytest.mark.asyncio
async def test_signup_rate_limit_rejects_by_normalized_email(monkeypatch):
    limit = settings.RATE_LIMIT_AUTH_PER_MINUTE

    store = ControlledRateStore(
        reject_bucket="signup:email:",
        limit=limit,
    )

    monkeypatch.setattr(
        auth_api,
        "_signup_rate_store",
        store,
    )

    canonical = f"rate-email-{uuid4()}@example.com"
    supplied = canonical.upper()

    transport = ASGITransport(
        app=app,
        client=("198.51.100.25", 12345),
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/signup",
            json=signup_payload(supplied),
        )

    assert response.status_code == 429

    expected_email = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

    assert any(key == f"signup:email:{expected_email}" for key in store.keys)


@pytest.mark.asyncio
async def test_signup_rate_limit_keys_do_not_contain_raw_email(monkeypatch):
    limit = settings.RATE_LIMIT_AUTH_PER_MINUTE

    store = ControlledRateStore(
        reject_bucket="never:",
        limit=limit,
    )

    monkeypatch.setattr(
        auth_api,
        "_signup_rate_store",
        store,
    )

    email = f"secret-rate-key-{uuid4()}@example.com"

    transport = ASGITransport(
        app=app,
        client=("192.0.2.50", 12345),
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/signup",
            json=signup_payload(email),
        )

    assert response.status_code == 201
    assert all(email not in key for key in store.keys)

    assert any(key.startswith("signup:ip:") for key in store.keys)
    assert any(key.startswith("signup:email:") for key in store.keys)
