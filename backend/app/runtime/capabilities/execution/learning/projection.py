from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.learning.contracts import (
    CapabilityLearningObservation,
)
from app.runtime.capabilities.execution.learning.repository import (
    CapabilityLearningObservationRepository,
)
from app.runtime.capabilities.execution.verification.repository import (
    TaskVerificationRepository,
)


class CapabilityLearningObservationProjector:
    """
    Convert one durable task-verification record into reusable learning evidence.

    Raw inputs, execution output, and evidence payload data are intentionally
    excluded. Only normalized outcome evidence is retained.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            CapabilityLearningObservationRepository
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or CapabilityLearningObservationRepository(
                db
            )
        )

    async def project_event(
        self,
        event: Any,
    ) -> dict[str, Any]:
        payload = dict(event.payload or {})

        raw_record_id = payload.get("record_id")

        if not raw_record_id:
            raise ValueError(
                "Task verification event "
                "record_id is required"
            )

        if event.user_id is None:
            raise ValueError(
                "Task verification event "
                "user_id is required"
            )

        record_id = UUID(str(raw_record_id))
        user_id = UUID(str(event.user_id))

        verification = await (
            TaskVerificationRepository(
                self.db
            ).get(
                user_id=user_id,
                record_id=record_id,
            )
        )

        if verification is None:
            raise ValueError(
                "Task verification record "
                f"not found for event: {record_id}"
            )

        observation = (
            self._build_observation(
                event=event,
                verification=verification,
            )
        )

        row, inserted = await (
            self.repository.record(
                observation=observation
            )
        )

        return {
            "source_event_id": str(event.id),
            "source_verification_record_id": (
                str(verification.id)
            ),
            "learning_observation_id": (
                str(row.id)
            ),
            "verification_id": (
                verification.verification_id
            ),
            "attempt_number": (
                verification.attempt_number
            ),
            "outcome": verification.outcome,
            "is_final": (
                not bool(verification.retryable)
            ),
            "inserted": inserted,
        }

    @staticmethod
    def _build_observation(
        *,
        event: Any,
        verification: Any,
    ) -> CapabilityLearningObservation:
        evidence = list(
            verification.evidence_json or []
        )

        evidence_summary = {
            "count": len(evidence),
            "items": [
                {
                    "kind": item.get("kind"),
                    "source": item.get(
                        "source"
                    ),
                    "observed_at_ts": item.get(
                        "observed_at_ts"
                    ),
                }
                for item in evidence
                if isinstance(item, dict)
            ],
        }

        request_metadata = dict(
            verification.request_metadata_json
            or {}
        )

        context = {
            "automatic": bool(
                request_metadata.get(
                    "automatic"
                )
            ),
            "source_capability_event_id": (
                request_metadata.get(
                    "source_event_id"
                )
            ),
            "source_capability_event_type": (
                request_metadata.get(
                    "source_event_type"
                )
            ),
        }

        return CapabilityLearningObservation(
            source_event_id=event.id,
            source_verification_record_id=(
                verification.id
            ),
            verification_id=(
                verification.verification_id
            ),
            attempt_number=(
                verification.attempt_number
            ),
            user_id=verification.user_id,
            tenant_id=verification.tenant_id,
            capability_id=(
                verification.capability_id
            ),
            provider_id=(
                verification.provider_id
            ),
            provider_ref=(
                verification.provider_ref
            ),
            action=verification.action,
            outcome=verification.outcome,
            method=verification.method,
            reason_code=(
                verification.reason_code
            ),
            confidence=(
                verification.confidence
            ),
            retryable=(
                verification.retryable
            ),
            is_final=(
                not bool(
                    verification.retryable
                )
            ),
            correlation_id=(
                verification.correlation_id
            ),
            workflow_run_id=(
                verification.workflow_run_id
            ),
            task_id=verification.task_id,
            summary=verification.summary,
            observed_outcome=dict(
                verification
                .observed_outcome_json
                or {}
            ),
            evidence_summary=evidence_summary,
            context=context,
            observed_at=(
                verification.completed_at
            ),
        )


__all__ = [
    "CapabilityLearningObservationProjector",
]
