import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_login_missing_password_returns_422():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/login",
            json={
                "email": "missing-password@example.com",
            },
        )

    assert response.status_code == 422

    body = response.json()

    assert any(error.get("loc") == ["body", "password"] for error in body["detail"])


@pytest.mark.asyncio
async def test_login_malformed_json_returns_422():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/login",
            content=b'{"email": ',
            headers={
                "content-type": "application/json",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.asyncio
async def test_login_missing_email_returns_422():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/auth/login",
            json={
                "password": "some-password",
            },
        )

    assert response.status_code == 422

    assert any(
        error.get("loc") == ["body", "email"] for error in response.json()["detail"]
    )
