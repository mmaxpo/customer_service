from __future__ import annotations

import asyncio
import sys
import time
import urllib.request
from pathlib import Path

from sqlalchemy import text

from app.core.session import engine
from app.core.config import settings


async def database_ready() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "api"
    try:
        if mode == "api":
            with urllib.request.urlopen(
                "http://127.0.0.1:8000/health/ready", timeout=3
            ) as response:
                return 0 if response.status == 200 else 1
        asyncio.run(database_ready())
        heartbeat = Path(settings.WORKER_HEARTBEAT_PATH)
        if not heartbeat.is_file():
            return 1
        if time.time() - heartbeat.stat().st_mtime > settings.WORKER_HEARTBEAT_MAX_AGE_SECONDS:
            return 1
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
