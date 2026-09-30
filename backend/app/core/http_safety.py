from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict

from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings

CSRF_COOKIE = "csrf_token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        raw_length = headers.get(b"content-length")
        if raw_length:
            try:
                if int(raw_length) > self.max_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                await self._reject(scope, receive, send)
                return

        chunks: list[bytes] = []
        total = 0
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            chunks.append(chunk)
            more = bool(message.get("more_body", False))

        body = b"".join(chunks)
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if sent:
                # Once the buffered request has been replayed, preserve the
                # transport's disconnect semantics for streaming responses.
                return await receive()
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            {"detail": "Request body too large"},
            status_code=413,
        )
        await response(scope, receive, send)


class RateLimitStore:
    def __init__(self, redis_url: str | None) -> None:
        self.redis = Redis.from_url(redis_url) if redis_url else None
        self._counts: dict[tuple[str, int], int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def current(self, key: str, *, window_seconds: int = 60) -> int:
        """Return the current fixed-window count without incrementing it."""
        window = int(time.time()) // window_seconds
        namespaced = f"tajeran:rate:{key}:{window}"

        if self.redis is not None:
            value = await self.redis.get(namespaced)
            return int(value or 0)

        async with self._lock:
            return int(self._counts.get((key, window), 0))

    async def reset(self, key: str, *, window_seconds: int = 60) -> None:
        """Clear the current fixed-window counter."""
        window = int(time.time()) // window_seconds
        namespaced = f"tajeran:rate:{key}:{window}"

        if self.redis is not None:
            await self.redis.delete(namespaced)
            return

        async with self._lock:
            self._counts.pop((key, window), None)

    async def increment(self, key: str, *, window_seconds: int = 60) -> int:
        window = int(time.time()) // window_seconds
        namespaced = f"tajeran:rate:{key}:{window}"
        if self.redis is not None:
            count = await self.redis.incr(namespaced)
            if count == 1:
                await self.redis.expire(namespaced, window_seconds + 2)
            return int(count)

        async with self._lock:
            map_key = (key, window)
            self._counts[map_key] += 1
            if len(self._counts) > 10_000:
                self._counts = {
                    item: value
                    for item, value in self._counts.items()
                    if item[1] >= window - 1
                }
            return self._counts[map_key]


class SecurityBoundaryMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.store = RateLimitStore(settings.REDIS_URL)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)

        if self._csrf_rejected(request):
            await JSONResponse(
                {"detail": "CSRF token missing or invalid"},
                status_code=403,
            )(scope, receive, send)
            return

        try:
            rate_limited = await self._rate_limited(request)
        except RedisError:
            await JSONResponse(
                {"detail": "Rate limiting temporarily unavailable"},
                status_code=503,
                headers={"Retry-After": "5"},
            )(scope, receive, send)
            return

        if rate_limited:
            await JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "60"},
            )(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _csrf_rejected(self, request: Request) -> bool:
        if not settings.CSRF_ENFORCED or request.method not in UNSAFE_METHODS:
            return False
        if request.url.path.endswith("/shopify/webhooks"):
            return False
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            return False
        if not request.cookies.get("access_token") and not request.cookies.get(
            "refresh_token"
        ):
            return False
        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get("x-csrf-token", "")
        return not (
            cookie_token
            and header_token
            and hmac.compare_digest(cookie_token, header_token)
        )

    async def _rate_limited(self, request: Request) -> bool:
        if not settings.RATE_LIMIT_ENABLED or os.getenv("PYTEST_CURRENT_TEST"):
            return False
        path = request.url.path
        if path == "/health/live":
            return False
        if path.startswith("/auth/"):
            bucket = "auth"
            limit = settings.RATE_LIMIT_AUTH_PER_MINUTE
        elif any(part in path for part in ("/agents", "/runs", "/workflows")):
            bucket = "agent"
            limit = settings.RATE_LIMIT_AGENT_PER_MINUTE
        else:
            bucket = "default"
            limit = settings.RATE_LIMIT_DEFAULT_PER_MINUTE
        workspace = request.headers.get("x-workspace-id")
        client = request.client.host if request.client else "unknown"
        identity = workspace or client
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        count = await self.store.increment(f"{bucket}:{digest}")
        return count > limit

    async def close(self) -> None:
        if self.store.redis is not None:
            await self.store.redis.aclose()


__all__ = [
    "CSRF_COOKIE",
    "RateLimitStore",
    "RequestBodyLimitMiddleware",
    "SecurityBoundaryMiddleware",
    "new_csrf_token",
]
