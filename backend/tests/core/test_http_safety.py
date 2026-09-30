from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.http_safety import (
    CSRF_COOKIE,
    RateLimitStore,
    RequestBodyLimitMiddleware,
    SecurityBoundaryMiddleware,
)


@pytest.mark.asyncio
async def test_request_body_limit_rejects_oversized_chunked_body():
    limited = FastAPI()

    @limited.post("/upload", status_code=204)
    async def upload():
        return None

    limited.add_middleware(RequestBodyLimitMiddleware, max_bytes=4)
    async with AsyncClient(
        transport=ASGITransport(app=limited),
        base_url="http://test",
    ) as client:
        response = await client.post("/upload", content=b"12345")
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_cookie_auth_requires_matching_csrf_token(monkeypatch):
    protected = FastAPI()

    @protected.post("/change", status_code=204)
    async def change():
        return None

    monkeypatch.setattr(settings, "CSRF_ENFORCED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    protected.add_middleware(SecurityBoundaryMiddleware)
    async with AsyncClient(
        transport=ASGITransport(app=protected),
        base_url="http://test",
    ) as client:
        client.cookies.set("access_token", "access")
        client.cookies.set(CSRF_COOKIE, "csrf-value")
        missing = await client.post("/change")
        matching = await client.post(
            "/change",
            headers={"x-csrf-token": "csrf-value"},
        )
    assert missing.status_code == 403
    assert matching.status_code == 204


@pytest.mark.asyncio
async def test_in_memory_rate_limit_store_counts_requests():
    store = RateLimitStore(None)
    assert await store.increment("test") == 1
    assert await store.increment("test") == 2


@pytest.mark.asyncio
async def test_liveness_bypasses_unavailable_redis(monkeypatch):
    protected = FastAPI()

    @protected.get("/health/live")
    async def liveness():
        return {"status": "alive"}

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    protected.add_middleware(SecurityBoundaryMiddleware)

    async def unavailable(*args, **kwargs):
        raise AssertionError("liveness must not contact Redis")

    middleware = protected.user_middleware[0]
    # Build the middleware stack so we can replace this instance's store.
    protected.middleware_stack = protected.build_middleware_stack()
    boundary = protected.middleware_stack.app
    monkeypatch.setattr(boundary.store, "increment", unavailable)

    async with AsyncClient(
        transport=ASGITransport(app=protected),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/live")

    assert middleware.cls is SecurityBoundaryMiddleware
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
