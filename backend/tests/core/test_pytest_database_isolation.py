from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.session import SessionLocal


@pytest.mark.asyncio
async def test_pytest_uses_an_isolated_database_without_provider_credentials():
    async with SessionLocal() as db:
        database_name = await db.scalar(text("select current_database()"))

    assert str(database_name).startswith("tajeran_pytest_")
    assert os.environ["APP_ENV"] == "testing"
    assert os.environ["OPENAI_API_KEY"] == "test-openai-key-never-send"
    assert os.environ["MCP_SEARCH_URL"] == "http://127.0.0.1:9"
