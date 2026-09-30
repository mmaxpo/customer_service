from __future__ import annotations

import functools
import time
from typing import Any

from app.domains.customer_service.repositories.audit_logs import AuditLogRepository


def _safe_action_meta(
    action: Any,
    *,
    status: str,
    duration_ms: float | None = None,
    error: Exception | None = None,
) -> dict:
    meta = {
        "observability": True,
        "status": status,
        "action_type": getattr(action, "action_type", None),
        "suggested_action_id": str(getattr(action, "id", "")),
        "conversation_id": str(getattr(action, "conversation_id", "")),
        "source": getattr(action, "source", None),
        "confidence": getattr(action, "confidence", None),
    }

    if duration_ms is not None:
        meta["duration_ms"] = round(duration_ms, 2)

    if error is not None:
        meta["error_type"] = error.__class__.__name__
        meta["error"] = str(error)[:500]

    return meta


async def _write_observation(
    db: Any,
    *,
    user_id: Any,
    action: Any,
    event: str,
    status: str,
    duration_ms: float | None = None,
    error: Exception | None = None,
) -> None:
    try:
        await AuditLogRepository(db).create(
            user_id=user_id,
            actor_id=user_id,
            entity_type="suggested_action",
            entity_id=getattr(action, "id", None),
            action=event,
            message=f"Suggested action {status}: {getattr(action, 'action_type', 'unknown')}",
            meta=_safe_action_meta(
                action,
                status=status,
                duration_ms=duration_ms,
                error=error,
            ),
        )
    except Exception:
        # Observability must never break the customer-service action path.
        try:
            await db.rollback()
        except Exception:
            pass


def observe_suggested_action_execution(fn):
    @functools.wraps(fn)
    async def wrapper(self, user_id, action, payload: dict):
        await _write_observation(
            self.db,
            user_id=user_id,
            action=action,
            event="suggested_action.execution.started",
            status="started",
        )

        started = time.perf_counter()

        try:
            result = await fn(self, user_id, action, payload)
        except Exception as exc:
            await _write_observation(
                self.db,
                user_id=user_id,
                action=action,
                event="suggested_action.execution.failed",
                status="failed",
                duration_ms=(time.perf_counter() - started) * 1000,
                error=exc,
            )
            raise

        await _write_observation(
            self.db,
            user_id=user_id,
            action=action,
            event="suggested_action.execution.completed",
            status="completed",
            duration_ms=(time.perf_counter() - started) * 1000,
        )

        return result

    return wrapper
