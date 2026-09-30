from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass, field
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import settings
from app.platform.realtime.schemas import RealtimeEvent


@dataclass
class RealtimeConnection:
    user_id: UUID
    scope: str | None = None
    queue: asyncio.Queue[RealtimeEvent | None] = field(
        default_factory=lambda: asyncio.Queue(maxsize=200)
    )
    pubsub: object | None = None
    listener_task: asyncio.Task | None = None


class RealtimeHub:
    """Replica-safe Redis fanout with a local development/test transport."""

    def __init__(self, *, redis_url: str | None = None) -> None:
        self._connections: dict[UUID, list[RealtimeConnection]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._redis_url = redis_url
        self._redis: Redis | None = None

    async def register(
        self, *, user_id: UUID, scope: str | None = None
    ) -> RealtimeConnection:
        connection = RealtimeConnection(user_id=user_id, scope=scope)
        async with self._lock:
            self._connections[user_id].append(connection)
        if self._redis_url:
            pubsub = self._redis_client().pubsub(ignore_subscribe_messages=True)
            await pubsub.subscribe(self._channel(user_id))
            connection.pubsub = pubsub
            connection.listener_task = asyncio.create_task(
                self._listen(connection), name=f"realtime:{user_id}"
            )
        return connection

    async def unregister(self, connection: RealtimeConnection) -> None:
        async with self._lock:
            connections = self._connections.get(connection.user_id)
            if connections and connection in connections:
                connections.remove(connection)
            if not connections:
                self._connections.pop(connection.user_id, None)
        if connection.listener_task:
            connection.listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await connection.listener_task
        if connection.pubsub:
            await connection.pubsub.aclose()
        await self._safe_put(connection, None)

    async def publish(self, event: RealtimeEvent) -> None:
        if self._redis_url:
            await self._redis_client().publish(
                self._channel(event.user_id), event.model_dump_json()
            )
            return
        await self._publish_local(event)

    async def count_for_user(self, user_id: UUID) -> int:
        async with self._lock:
            return len(self._connections.get(user_id, ()))

    async def close(self) -> None:
        async with self._lock:
            connections = [item for rows in self._connections.values() for item in rows]
        for connection in connections:
            await self.unregister(connection)
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def _listen(self, connection: RealtimeConnection) -> None:
        while True:
            message = await connection.pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if not message:
                await asyncio.sleep(0.01)
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            event = RealtimeEvent.model_validate_json(data)
            if not connection.scope or connection.scope == event.scope:
                await self._safe_put(connection, event)

    async def _publish_local(self, event: RealtimeEvent) -> None:
        async with self._lock:
            targets = list(self._connections.get(event.user_id, ()))
        for connection in targets:
            if not connection.scope or connection.scope == event.scope:
                await self._safe_put(connection, event)

    def _redis_client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=False)
        return self._redis

    @staticmethod
    def _channel(user_id: UUID) -> str:
        return f"tajeran:realtime:{user_id}"

    @staticmethod
    async def _safe_put(connection, event) -> None:
        try:
            connection.queue.put_nowait(event)
        except asyncio.QueueFull:
            with suppress(asyncio.QueueEmpty):
                connection.queue.get_nowait()
            connection.queue.put_nowait(event)


realtime_hub = RealtimeHub(redis_url=settings.REDIS_URL)
