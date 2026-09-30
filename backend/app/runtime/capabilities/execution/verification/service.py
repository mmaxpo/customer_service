from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    TaskVerificationRecord,
)
from app.runtime.capabilities.execution.verification.contracts import (
    TaskVerificationContext,
    TaskVerificationEvidence,
    TaskVerificationExecution,
    TaskVerificationMethod,
    TaskVerificationOutcome,
    TaskVerificationRequest,
    TaskVerificationResult,
)
from app.runtime.capabilities.execution.verification.defaults import (
    build_default_task_verifier_registry,
)
from app.runtime.capabilities.execution.verification.events import (
    TaskVerificationLifecycleEvents,
)
from app.runtime.capabilities.execution.verification.registry import (
    TaskVerifierRegistry,
)
from app.runtime.capabilities.execution.verification.repository import (
    TaskVerificationRepository,
    normalize_verification_idempotency_key,
    normalize_verification_user_id,
)


class TaskVerificationService:
    """
    Execute, persist, and publish one task-verification attempt atomically.

    The idempotency lock is acquired before remote verification. This prevents
    duplicate deliveries from repeating a provider read when an existing
    durable attempt already owns the idempotency key.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        services: Any = None,
        registry: (
            TaskVerifierRegistry | None
        ) = None,
        repository: (
            TaskVerificationRepository | None
        ) = None,
        lifecycle_events: (
            TaskVerificationLifecycleEvents
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.services = services
        self.registry = (
            registry
            or build_default_task_verifier_registry()
        )
        self.repository = (
            repository
            or TaskVerificationRepository(db)
        )
        self.lifecycle_events = (
            lifecycle_events
            or TaskVerificationLifecycleEvents(
                db
            )
        )

    async def verify(
        self,
        *,
        user_id: UUID | str,
        request: TaskVerificationRequest,
        idempotency_key: str,
    ) -> TaskVerificationExecution:
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

        self._validate_request_owner(
            authenticated_user_id=(
                normalized_user_id
            ),
            request=request,
        )

        await self._lock_idempotency_key(
            user_id=normalized_user_id,
            idempotency_key=normalized_key,
        )

        existing = await (
            self.repository
            .get_by_idempotency_key(
                user_id=normalized_user_id,
                idempotency_key=(
                    normalized_key
                ),
            )
        )

        if existing is not None:
            return self._execution_from_record(
                existing,
                created=False,
            )

        verifier_failed = False

        try:
            result = await self.registry.verify(
                TaskVerificationContext(
                    request=request,
                    services=self.services,
                )
            )
        except Exception as exc:
            verifier_failed = True
            result = self._failed_result(
                request=request,
                exc=exc,
            )

        try:
            record = await (
                self.repository.append_attempt(
                    user_id=normalized_user_id,
                    request=request,
                    result=result,
                    idempotency_key=(
                        normalized_key
                    ),
                )
            )

            if verifier_failed:
                await (
                    self.lifecycle_events.failed(
                        user_id=normalized_user_id,
                        record=record,
                        request=request,
                        result=result,
                    )
                )
            else:
                await (
                    self.lifecycle_events.completed(
                        user_id=normalized_user_id,
                        record=record,
                        request=request,
                        result=result,
                    )
                )

            await (
                self.lifecycle_events
                .business_outcome(
                    user_id=normalized_user_id,
                    record=record,
                    request=request,
                    result=result,
                )
            )

            await self.db.commit()
            await self.db.refresh(record)

            return TaskVerificationExecution(
                record_id=str(record.id),
                attempt_number=(
                    record.attempt_number
                ),
                created=True,
                result=result,
            )
        except Exception:
            await self.db.rollback()
            raise

    async def _lock_idempotency_key(
        self,
        *,
        user_id: UUID,
        idempotency_key: str,
    ) -> None:
        lock_key = (
            "task_verification_idempotency:"
            f"{user_id}:"
            f"{idempotency_key}"
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

    @staticmethod
    def _validate_request_owner(
        *,
        authenticated_user_id: UUID,
        request: TaskVerificationRequest,
    ) -> None:
        if request.user_id is None:
            return

        request_user_id = (
            normalize_verification_user_id(
                request.user_id
            )
        )

        if (
            request_user_id
            != authenticated_user_id
        ):
            raise ValueError(
                "task verification request "
                "user_id does not match "
                "authenticated user"
            )

    @staticmethod
    def _failed_result(
        *,
        request: TaskVerificationRequest,
        exc: Exception,
    ) -> TaskVerificationResult:
        return TaskVerificationResult(
            verification_id=(
                request.verification_id
            ),
            capability_id=(
                request.capability_id
            ),
            provider_id=request.provider_id,
            provider_ref=request.provider_ref,
            action=(
                request.action
                or request.inputs.get("action")
            ),
            outcome=(
                TaskVerificationOutcome
                .INCONCLUSIVE
            ),
            method=(
                TaskVerificationMethod
                .EXECUTION_EVIDENCE
            ),
            reason_code=(
                "verifier_execution_failed"
            ),
            summary=(
                "The verification process failed "
                "before a business outcome could "
                "be established."
            ),
            confidence=0.0,
            retryable=True,
            observed_outcome={},
            evidence=[
                TaskVerificationEvidence(
                    kind=(
                        "verification_execution_error"
                    ),
                    source=(
                        "task_verification_service"
                    ),
                    data={
                        "exception_type": (
                            type(exc).__name__
                        ),
                    },
                )
            ],
        )

    @staticmethod
    def _execution_from_record(
        record: TaskVerificationRecord,
        *,
        created: bool,
    ) -> TaskVerificationExecution:
        result = TaskVerificationResult(
            verification_id=(
                record.verification_id
            ),
            capability_id=(
                record.capability_id
            ),
            provider_id=(
                record.provider_id
            ),
            provider_ref=(
                record.provider_ref
            ),
            action=record.action,
            outcome=TaskVerificationOutcome(
                record.outcome
            ),
            method=TaskVerificationMethod(
                record.method
            ),
            reason_code=(
                record.reason_code
            ),
            summary=record.summary,
            confidence=record.confidence,
            retryable=record.retryable,
            observed_outcome=dict(
                record.observed_outcome_json
                or {}
            ),
            evidence=[
                TaskVerificationEvidence
                .model_validate(item)
                for item in (
                    record.evidence_json or []
                )
            ],
            completed_at_ts=(
                record.completed_at.timestamp()
            ),
        )

        return TaskVerificationExecution(
            record_id=str(record.id),
            attempt_number=(
                record.attempt_number
            ),
            created=created,
            result=result,
        )


__all__ = [
    "TaskVerificationService",
]
