from __future__ import annotations

from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings


@asynccontextmanager
async def lifespan_checkpointer():
    """
    Creates a Postgres-backed LangGraph checkpointer.

    Why:
    - Required for interrupt()/resume()
    - Required for persistence and time-travel debugging
    - Stores checkpoints keyed by thread_id
    """
    async with AsyncPostgresSaver.from_conn_string(
        settings.LANGGRAPH_CHECKPOINT_DB_URL
    ) as saver:
        # Must be called once to create tables/migrations for the saver
        await saver.setup()
        yield saver
