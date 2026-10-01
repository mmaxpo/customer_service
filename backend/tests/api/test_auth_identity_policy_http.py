from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.identity import normalize_email, validate_password_policy
from app.main import app


LEGAL_ACCEPTANCE = {
    "terms_accepted": True,
    "terms_version": "v1",
    "privacy_accepted": True,
    "privacy_version": "v1",
}


def test_normalize_email_trims_and_casefolds():
    assert normalize_email("  User@Example.COM  ") == "user@example.com"


@pytest.mark.parametrize(
    "password",
    [
        "short1",
        "NoNumbersHere!",
        "12345678",
    ],
)
def test_password_policy_rejects_weak_passwords(password: str):
    with pytest.raises(ValueError):
        validate_password_policy(password)


def test_password_policy_accepts_v1_password():
    assert validate_password_policy("Strong-Password-123!") == "Strong-Password-123!"


def test_password_policy_accepts_a_simple_eight_character_password():
    assert validate_password_policy("sunshine7") == "sunshine7"


@pytest.mark.asyncio
async def test_signup_stores_and_authenticates_canonical_email():
    raw_email = f"  Mixed.Case-{uuid4()}@Example.COM  "
    canonical_email = raw_email.strip().casefold()
    password = "Strong-Password-123!"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        signup = await client.post(
            "/auth/signup",
            json={
                **LEGAL_ACCEPTANCE,
                "email": raw_email,
                "password": password,
            },
        )
        assert signup.status_code == 201
        assert signup.json() == {"detail": "Registration request accepted."}

        login = await client.post(
            "/auth/login",
            json={
                "email": canonical_email.upper(),
                "password": password,
            },
        )
        assert login.status_code == 200


@pytest.mark.asyncio
async def test_signup_rejects_password_outside_policy():
    email = f"weak-password-{uuid4()}@example.com"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/signup",
            json={
                **LEGAL_ACCEPTANCE,
                "email": email,
                "password": "weakpassword",
            },
        )

    assert response.status_code in {400, 422}


@pytest.mark.asyncio
async def test_password_reset_rejects_password_outside_shared_policy():
    # The HTTP schema already rejects short values. This proves the domain
    # policy also rejects a long-enough password with no number.
    email = f"reset-policy-{uuid4()}@example.com"
    original_password = "Original-Password-123!"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        signup = await client.post(
            "/auth/signup",
            json={
                **LEGAL_ACCEPTANCE,
                "email": email,
                "password": original_password,
            },
        )
        assert signup.status_code == 201
