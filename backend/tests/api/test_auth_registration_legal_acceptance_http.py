from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.session import SessionLocal
from app.main import app
from app.models.models import User


def valid_signup(email: str) -> dict[str, object]:
    return {
        "email": email,
        "password": "Strong-Password-123!",
        "terms_accepted": True,
        "terms_version": "terms-2026-09",
        "privacy_accepted": True,
        "privacy_version": "privacy-2026-09",
    }


@pytest.mark.asyncio
async def test_signup_requires_terms_acceptance():
    payload = valid_signup(f"terms-required-{uuid4()}@example.com")
    payload["terms_accepted"] = False

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/signup",
            json=payload,
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_requires_privacy_acceptance():
    payload = valid_signup(f"privacy-required-{uuid4()}@example.com")
    payload["privacy_accepted"] = False

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/signup",
            json=payload,
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_persists_legal_versions_and_server_timestamp():
    email = f"legal-persist-{uuid4()}@example.com"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/signup",
            json=valid_signup(email),
        )

    assert response.status_code == 201

    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(User.normalized_email == email)
        )
        user = result.scalar_one()

        assert user.email == email
        assert user.normalized_email == email

        assert user.terms_accepted_at is not None
        assert user.terms_version == "terms-2026-09"

        assert user.privacy_accepted_at is not None
        assert user.privacy_version == "privacy-2026-09"


@pytest.mark.asyncio
async def test_canonical_email_is_persisted_in_normalized_column():
    canonical = f"canonical-{uuid4()}@example.com"
    mixed = canonical.upper()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/signup",
            json=valid_signup(mixed),
        )

    assert response.status_code == 201

    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(User.normalized_email == canonical)
        )
        user = result.scalar_one()

        assert user.normalized_email == canonical
        assert user.email == canonical
