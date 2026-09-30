"""Verify empty-database upgrades and the supported one-step rollback."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402


async def _database(database_url: str, name: str, *, create: bool) -> None:
    admin_url = make_url(database_url).set(database="postgres")
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            if create:
                await connection.execute(text(f'CREATE DATABASE "{name}"'))
            else:
                await connection.execute(
                    text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
                )
    finally:
        await engine.dispose()


async def main() -> None:
    name = f"tajeran_migration_check_{uuid.uuid4().hex[:10]}"
    database_url = make_url(settings.DATABASE_URL).set(database=name).render_as_string(
        hide_password=False
    )
    await _database(settings.DATABASE_URL, name, create=True)
    env = {**os.environ, "DATABASE_URL": database_url}
    try:
        command = [sys.executable, "-m", "alembic"]
        subprocess.run([*command, "upgrade", "head"], env=env, check=True)
        subprocess.run([*command, "downgrade", "-1"], env=env, check=True)
        subprocess.run([*command, "upgrade", "head"], env=env, check=True)
        subprocess.run([*command, "current"], env=env, check=True)
    finally:
        await _database(settings.DATABASE_URL, name, create=False)


if __name__ == "__main__":
    asyncio.run(main())
