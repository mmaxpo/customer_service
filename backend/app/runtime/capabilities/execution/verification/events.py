from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.events.publisher import (
    PlatformEventPublisher,
)
from app.runtime.capabilities.execution.verification.contracts import (
    TaskVerificationOutcome,
    TaskVerificationRequest,
    TaskVerificationResult,
)


TASK_VERIFICATION_COMPLETED_EVENT = (
    "runtime.task.verification.completed"
)
TASK_VERIFICATION_FAILED_EVENT = (
    "runtime.task.verification.failed"
)

TASK_OUTCOME_VERIFIED_EVENT = (
    "runtime.task.outcome.verified"
)
TASK_OUTCOME_NOT_ACHIEVED_EVENT = (
    "runtime.task.outcome.not_achieved"
)
TASK_OUTCOME_INCONCLUSIVE_EVENT = (
    "runtime.task.outcome.inconclusive"
)
TASK_OUTCOME_PARTIALLY_VERIFIED_EVENT = (
    "runtime.task.outcome.partially_verified"
)
TASK_OUTCOME_NOT_VERIFIABLE_EVENT = (
    "runtime.task.outcome.not_verifiable"
)

TASK_VERIFICATION_EVENT_SOURCE = (
    "runtime.task_verification"
)


class TaskVerificationLifecycleEvents:
    """
    Transaction-aware, secret-minimizing verification event publisher.

    Events intentionally omit raw inputs, execution output, and evidence data.
    Those remain in the user-scoped durable verification record.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.publisher = PlatformEventPublisher(
            db
        )

    async def completed(
        self,
        *,
        user_id: Any,
        record,
        request: TaskVerificationRequest,
        result: TaskVerificationResult,
    ) -> None:
        await self._publish(
            event_type=(
                TASK_VERIFICATION_COMPLETED_EVENT
            ),
            user_id=user_id,
            record=record,
            request=request,
            result=result,
        )

    async def failed(
        self,
        *,
        user_id: Any,
        record,
        request: TaskVerificationRequest,
        result: TaskVerificationResult,
    ) -> None:
        await self._publish(
            event_type=(
                TASK_VERIFICATION_FAILED_EVENT
            ),
            user_id=user_id,
            record=record,
            request=request,
            result=result,
        )

    async def business_outcome(
        self,
        *,
        user_id: Any,
        record,
        request: TaskVerificationRequest,
        result: TaskVerificationResult,
    ) -> None:
        event_type = (
            self._outcome_event_type(
                result.outcome
            )
        )

        await self._publish(
            event_type=event_type,
            user_id=user_id,
            record=record,
            request=request,
            result=result,
        )

    async def _publish(
        self,
        *,
        event_type: str,
        user_id: Any,
        record,
        request: TaskVerificationRequest,
        result: TaskVerificationResult,
    ) -> None:
        await self.publisher.publish(
            user_id=user_id,
            event_type=event_type,
            source=(
                TASK_VERIFICATION_EVENT_SOURCE
            ),
            payload={
                "record_id": str(record.id),
                "verification_id": (
                    record.verification_id
                ),
                "attempt_number": (
                    record.attempt_number
                ),
                "capability_id": (
                    result.capability_id
                ),
                "provider_id": (
                    result.provider_id
                ),
                "provider_ref": (
                    result.provider_ref
                ),
                "action": result.action,
                "outcome": (
                    result.outcome.value
                ),
                "method": result.method.value,
                "reason_code": (
                    result.reason_code
                ),
                "confidence": (
                    result.confidence
                ),
                "retryable": (
                    result.retryable
                ),
            },
            meta={
                "tenant_id": (
                    request.tenant_id
                ),
                "correlation_id": (
                    request.correlation_id
                ),
                "workflow_run_id": (
                    request.workflow_run_id
                ),
                "task_id": request.task_id,
            },
            dispatch=False,
            commit=False,
        )

    @staticmethod
    def _outcome_event_type(
        outcome: TaskVerificationOutcome,
    ) -> str:
        mapping = {
            TaskVerificationOutcome.VERIFIED: (
                TASK_OUTCOME_VERIFIED_EVENT
            ),
            TaskVerificationOutcome.FAILED: (
                TASK_OUTCOME_NOT_ACHIEVED_EVENT
            ),
            TaskVerificationOutcome.INCONCLUSIVE: (
                TASK_OUTCOME_INCONCLUSIVE_EVENT
            ),
            TaskVerificationOutcome.PARTIALLY_VERIFIED: (
                TASK_OUTCOME_PARTIALLY_VERIFIED_EVENT
            ),
            TaskVerificationOutcome.NOT_VERIFIABLE: (
                TASK_OUTCOME_NOT_VERIFIABLE_EVENT
            ),
        }

        return mapping[outcome]


__all__ = [
    "TASK_OUTCOME_INCONCLUSIVE_EVENT",
    "TASK_OUTCOME_NOT_ACHIEVED_EVENT",
    "TASK_OUTCOME_NOT_VERIFIABLE_EVENT",
    "TASK_OUTCOME_PARTIALLY_VERIFIED_EVENT",
    "TASK_OUTCOME_VERIFIED_EVENT",
    "TASK_VERIFICATION_COMPLETED_EVENT",
    "TASK_VERIFICATION_EVENT_SOURCE",
    "TASK_VERIFICATION_FAILED_EVENT",
    "TaskVerificationLifecycleEvents",
]
