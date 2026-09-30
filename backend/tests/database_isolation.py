from __future__ import annotations

import atexit
import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from sqlalchemy.engine import URL, make_url


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_database_name: str | None = None
_admin_url: str | None = None
_cleaned = False


def _source_database_url() -> URL:
    raw_url = os.environ.get("TAJERAN_TEST_ADMIN_DATABASE_URL")

    if not raw_url:
        raw_url = os.environ.get("DATABASE_URL")

    if not raw_url:
        raw_url = str(
            dotenv_values(_REPOSITORY_ROOT / ".env.dev").get("DATABASE_URL") or ""
        )

    if not raw_url:
        raise RuntimeError(
            "Tests require DATABASE_URL or a configured .env.dev PostgreSQL URL"
        )

    return make_url(raw_url)


def _psycopg_url(url: URL, *, database: str) -> str:
    return url.set(
        drivername="postgresql",
        database=database,
    ).render_as_string(hide_password=False)


def _asyncpg_url(url: URL, *, database: str) -> str:
    return url.set(
        drivername="postgresql+asyncpg",
        database=database,
    ).render_as_string(hide_password=False)


def _create_database(admin_url: str, database_name: str) -> None:
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )


def _drop_database() -> None:
    global _cleaned

    if _cleaned or not _admin_url or not _database_name:
        return

    _cleaned = True

    try:
        with psycopg.connect(_admin_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(_database_name)
                )
            )
    except Exception:
        # Do not hide the actual pytest result during interpreter shutdown.
        pass


def bootstrap_isolated_test_database() -> str:
    """Create and migrate a database that no development worker can consume."""

    global _admin_url, _database_name

    if _database_name:
        return _database_name

    source_environment = (
        (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development")
        .strip()
        .lower()
    )
    if source_environment in {"prod", "production", "stage", "staging"}:
        raise RuntimeError(
            "Refusing to create a pytest database from a production/staging environment"
        )

    source_url = _source_database_url()
    _database_name = f"tajeran_pytest_{os.getpid()}_{uuid.uuid4().hex[:10]}"

    admin_database = os.environ.get("TAJERAN_TEST_ADMIN_DATABASE") or "postgres"
    _admin_url = _psycopg_url(source_url, database=admin_database)
    _create_database(_admin_url, _database_name)

    os.environ["APP_ENV"] = "testing"
    os.environ["DATABASE_URL"] = _asyncpg_url(
        source_url,
        database=_database_name,
    )
    os.environ["LANGGRAPH_CHECKPOINT_DB_URL"] = _psycopg_url(
        source_url,
        database=_database_name,
    )
    os.environ.setdefault("SECRET_KEY", "isolated-pytest-secret-not-for-production")

    # A developer shell may export real provider credentials. Replace them
    # with inert values so runtime composition remains constructible while a
    # test can never spend merchant/developer provider quota.
    os.environ["OPENAI_API_KEY"] = "test-openai-key-never-send"
    os.environ["MCP_SEARCH_URL"] = "http://127.0.0.1:9"
    os.environ["MCP_API_KEY"] = "test-mcp-key-never-send"
    os.environ.setdefault("MCP_SEARCH_PATH", "/mcp/search")

    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_REPOSITORY_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if migration.returncode != 0:
        _drop_database()
        raise RuntimeError(
            "Could not migrate isolated pytest database:\n"
            f"{migration.stdout}\n{migration.stderr}"
        )

    atexit.register(_drop_database)
    return _database_name


def cleanup_isolated_test_database() -> None:
    _drop_database()


__all__ = [
    "bootstrap_isolated_test_database",
    "cleanup_isolated_test_database",
]
