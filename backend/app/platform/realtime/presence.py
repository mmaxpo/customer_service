from __future__ import annotations

from uuid import UUID, uuid4

from redis.asyncio import Redis

from app.core.config import settings


class PresenceLease:
    """Distributed, TTL-backed connection leases; no DB heartbeat writes."""
    def __init__(self, redis: Redis | None = None):
        self.redis = redis or (Redis.from_url(settings.REDIS_URL, decode_responses=True) if settings.REDIS_URL else None)

    async def heartbeat(self, *, workspace_id: UUID, agent_user_id: UUID, connection_id: str | None = None, ttl: int | None = None) -> str:
        connection_id = connection_id or str(uuid4())
        if self.redis:
            await self.redis.set(self.key(workspace_id, agent_user_id, connection_id), "1", ex=ttl or settings.AGENT_PRESENCE_LEASE_SECONDS)
        return connection_id

    async def release(self, *, workspace_id: UUID, agent_user_id: UUID, connection_id: str) -> None:
        if self.redis:
            await self.redis.delete(self.key(workspace_id, agent_user_id, connection_id))

    async def release_session(self, session_id: str) -> None:
        """Logout cleanup for one authenticated session, preserving other tabs."""
        if not self.redis:
            return
        cursor = 0
        match = f"tajeran:presence:*:*:{session_id}:*"
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=match, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

    async def has_any(self, *, workspace_id: UUID, agent_user_id: UUID) -> bool:
        if not self.redis:
            return False
        cursor = 0
        match = f"tajeran:presence:{workspace_id}:{agent_user_id}:*"
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=match, count=10)
            if keys:
                return True
            if cursor == 0:
                return False

    @staticmethod
    def key(workspace_id: UUID, agent_user_id: UUID, connection_id: str) -> str:
        return f"tajeran:presence:{workspace_id}:{agent_user_id}:{connection_id}"
