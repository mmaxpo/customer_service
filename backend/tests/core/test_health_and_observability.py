from __future__ import annotations

import json
import logging

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from httpx import ASGITransport, AsyncClient

from app.core.observability import JsonFormatter
from app.main import app


@pytest.mark.asyncio
async def test_readiness_requires_database_at_migration_head():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/health/ready",
            headers={"x-request-id": "readiness-test"},
        )
    assert response.status_code == 200
    expected_head = ScriptDirectory.from_config(
        Config("alembic.ini")
    ).get_current_head()
    assert response.json()["database_revision"] == expected_head
    assert response.headers["x-request-id"] == "readiness-test"


def test_json_formatter_emits_machine_readable_context():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.status_code = 200
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "request_completed"
    assert payload["request_id"] == "request-123"
    assert payload["status_code"] == 200


def test_json_formatter_preserves_llm_resilience_dimensions():
    record = logging.LogRecord(
        name="tajeran.llm.resilience",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="llm_provider_retry_scheduled",
        args=(),
        exc_info=None,
    )
    record.provider = "openai"
    record.failure_code = "llm_rate_limited"
    record.retryable = True
    record.attempt = 1
    record.max_attempts = 3
    record.retry_in_seconds = 2.5

    payload = json.loads(JsonFormatter().format(record))

    assert payload["provider"] == "openai"
    assert payload["failure_code"] == "llm_rate_limited"
    assert payload["retryable"] is True
    assert payload["attempt"] == 1
    assert payload["max_attempts"] == 3
    assert payload["retry_in_seconds"] == 2.5
