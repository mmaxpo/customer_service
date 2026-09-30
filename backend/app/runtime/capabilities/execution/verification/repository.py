from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    TaskVerificationRecord,
)
from app.runtime.capabilities.execution.verification.contracts import (
    TaskVerificationRequest,
    TaskVerificationResult,
)


def normalize_verification_user_id(
    value: Any,
) -> UUID:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        raise ValueError(
            "user_id must be a valid UUID"
        ) from exc


def normalize_verification_id(
    value: Any,
) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise ValueError(
            "verification_id is required"
        )

    return normalized


def normalize_verification_idempotency_key(
    value: Any,
) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise ValueError(
            "idempotency_key is required"
        )

    return normalized


class TaskVerificationRepository:
    """
    Append-only task-verification persistence.

    Writes flush but do not commit. The calling service owns the transaction,
    allowing verification state, events, and related projections to commit or
    roll back together.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def append_attempt(
        self,
        *,
        user_id: UUID | str,
        request: TaskVerificationRequest,
        result: TaskVerificationResult,
        idempotency_key: str,
    ) -> TaskVerificationRecord:
        normalized_user_id = (
            normalize_verification_user_id(
                user_id
            )
        )
        verification_id = (
            normalize_verification_id(
                request.verification_id
            )
        )
        normalized_idempotency_key = (
            normalize_verification_idempotency_key(
                idempotency_key
            )
        )

        if (
            result.verification_id
            != verification_id
        ):
            raise ValueError(
                "verification result does not "
                "match request verification_id"
            )

        if (
            result.capability_id
            != request.capability_id
        ):
            raise ValueError(
                "verification result does not "
                "match request capability_id"
            )

        lock_key = (
            "task_verification:"
            f"{normalized_user_id}:"
            f"{verification_id}"
        )

        await self.db.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtextextended(:lock_key, 0)"
                ")"
            ),
            {
                "lock_key": lock_key,
            },
        )

        existing = await self.get_by_idempotency_key(
            user_id=normalized_user_id,
            idempotency_key=(
                normalized_idempotency_key
            ),
        )

        if existing is not None:
            return existing

        current_attempt = await self.db.scalar(
            select(
                func.max(
                    TaskVerificationRecord
                    .attempt_number
                )
            ).where(
                TaskVerificationRecord.user_id
                == normalized_user_id,
                TaskVerificationRecord
                .verification_id
                == verification_id,
            )
        )

        attempt_number = (
            int(current_attempt or 0) + 1
        )

        record = TaskVerificationRecord(
            verification_id=verification_id,
            idempotency_key=(
                normalized_idempotency_key
            ),
            user_id=normalized_user_id,
            tenant_id=request.tenant_id,
            capability_id=(
                request.capability_id
            ),
            provider_id=(
                result.provider_id
                or request.provider_id
            ),
            provider_ref=(
                result.provider_ref
                or request.provider_ref
            ),
            action=(
                result.action
                or request.action
                or request.inputs.get("action")
            ),
            correlation_id=(
                request.correlation_id
            ),
            workflow_run_id=(
                request.workflow_run_id
            ),
            task_id=request.task_id,
            attempt_number=attempt_number,
            outcome=result.outcome.value,
            method=result.method.value,
            reason_code=(
                result.reason_code
            ),
            summary=result.summary,
            confidence=result.confidence,
            retryable=result.retryable,
            inputs_json=dict(
                request.inputs or {}
            ),
            requested_outcome_json=dict(
                request.expected_outcome or {}
            ),
            execution_output_json=(
                request.execution_output
            ),
            observed_outcome_json=dict(
                result.observed_outcome or {}
            ),
            evidence_json=[
                item.model_dump(mode="json")
                for item in result.evidence
            ],
            request_metadata_json=dict(
                request.metadata or {}
            ),
            requested_at=(
                datetime.fromtimestamp(
                    request.requested_at_ts,
                    tz=timezone.utc,
                )
            ),
            completed_at=(
                datetime.fromtimestamp(
                    result.completed_at_ts,
                    tz=timezone.utc,
                )
            ),
        )

        self.db.add(record)
        await self.db.flush()

        return record

    async def get(
        self,
        *,
        user_id: UUID | str,
        record_id: UUID,
    ) -> TaskVerificationRecord | None:
        normalized_user_id = (
            normalize_verification_user_id(
                user_id
            )
        )

        result = await self.db.execute(
            select(TaskVerificationRecord)
            .where(
                TaskVerificationRecord.id
                == record_id,
                TaskVerificationRecord.user_id
                == normalized_user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self,
        *,
        user_id: UUID | str,
        idempotency_key: str,
    ) -> TaskVerificationRecord | None:
        normalized_user_id = (
            normalize_verification_user_id(
                user_id
            )
        )
        normalized_key = (
            normalize_verification_idempotency_key(
                idempotency_key
            )
        )

        result = await self.db.execute(
            select(TaskVerificationRecord)
            .where(
                TaskVerificationRecord.user_id
                == normalized_user_id,
                TaskVerificationRecord
                .idempotency_key
                == normalized_key,
            )
        )

        return result.scalar_one_or_none()

    async def list_attempts(
        self,
        *,
        user_id: UUID | str,
        verification_id: str,
    ) -> list[TaskVerificationRecord]:
        normalized_user_id = (
            normalize_verification_user_id(
                user_id
            )
        )
        normalized_verification_id = (
            normalize_verification_id(
                verification_id
            )
        )

        result = await self.db.execute(
            select(TaskVerificationRecord)
            .where(
                TaskVerificationRecord.user_id
                == normalized_user_id,
                TaskVerificationRecord
                .verification_id
                == normalized_verification_id,
            )
            .order_by(
                TaskVerificationRecord
                .attempt_number
                .asc(),
            )
        )

        return list(result.scalars().all())

    async def list_for_user(
        self,
        *,
        user_id: UUID | str,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        correlation_id: str | None = None,
        workflow_run_id: str | None = None,
        task_id: str | None = None,
        retryable: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TaskVerificationRecord]:
        normalized_user_id = (
            normalize_verification_user_id(
                user_id
            )
        )

        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        if offset < 0:
            raise ValueError(
                "offset must be >= 0"
            )

        stmt = (
            select(TaskVerificationRecord)
            .where(
                TaskVerificationRecord.user_id
                == normalized_user_id
            )
            .order_by(
                TaskVerificationRecord
                .created_at
                .desc(),
                TaskVerificationRecord
                .attempt_number
                .desc(),
                TaskVerificationRecord.id
                .desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        filters = (
            (
                TaskVerificationRecord.tenant_id,
                tenant_id,
            ),
            (
                TaskVerificationRecord.capability_id,
                capability_id,
            ),
            (
                TaskVerificationRecord.provider_id,
                provider_id,
            ),
            (
                TaskVerificationRecord.action,
                action,
            ),
            (
                TaskVerificationRecord.outcome,
                outcome,
            ),
            (
                TaskVerificationRecord
                .correlation_id,
                correlation_id,
            ),
            (
                TaskVerificationRecord
                .workflow_run_id,
                workflow_run_id,
            ),
            (
                TaskVerificationRecord.task_id,
                task_id,
            ),
        )

        for column, value in filters:
            if value is not None:
                stmt = stmt.where(
                    column == value
                )

        if retryable is not None:
            stmt = stmt.where(
                TaskVerificationRecord.retryable
                == bool(retryable)
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())


__all__ = [
    "TaskVerificationRepository",
    "normalize_verification_id",
    "normalize_verification_idempotency_key",
    "normalize_verification_user_id",
]
