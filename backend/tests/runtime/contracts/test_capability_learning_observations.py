from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningObservationProjector,
    CapabilityLearningObservationRepository,
)
from app.runtime.capabilities.execution.verification import (
    TASK_VERIFICATION_COMPLETED_EVENT,
    TaskVerificationEvidence,
    TaskVerificationMethod,
    TaskVerificationOutcome,
    TaskVerificationRepository,
    TaskVerificationRequest,
    TaskVerificationResult,
)


@pytest.mark.asyncio
async def test_learning_projection_is_idempotent_and_secret_minimized():
    user_id = uuid4()
    verification_id = (
        f"learning-{uuid4()}"
    )

    request = TaskVerificationRequest(
        verification_id=verification_id,
        capability_id=(
            "ecommerce.orders.manage"
        ),
        provider_id="shopify",
        provider_ref="shopify.order_action",
        action="refund",
        user_id=str(user_id),
        tenant_id="tenant-learning",
        correlation_id="corr-learning",
        workflow_run_id="run-learning",
        task_id="task-learning",
        inputs={
            "action": "refund",
            "order_ref": "#9001",
            "note": "private customer note",
        },
        expected_outcome={
            "refund_prepared": True,
        },
        execution_output={
            "private": "provider response",
        },
        metadata={
            "automatic": True,
            "source_event_id": "cap-event-1",
            "source_event_type": (
                "runtime.capability."
                "execution.completed"
            ),
        },
    )

    result = TaskVerificationResult(
        verification_id=verification_id,
        capability_id=(
            request.capability_id
        ),
        provider_id="shopify",
        provider_ref="shopify.order_action",
        action="refund",
        outcome=(
            TaskVerificationOutcome
            .PARTIALLY_VERIFIED
        ),
        method=(
            TaskVerificationMethod
            .EXECUTION_EVIDENCE
        ),
        reason_code=(
            "refund_prepared_not_completed"
        ),
        summary=(
            "Refund preparation succeeded."
        ),
        confidence=0.85,
        retryable=False,
        observed_outcome={
            "refund_prepared": True,
            "refund_completed": False,
        },
        evidence=[
            TaskVerificationEvidence(
                kind="execution_result",
                source="shopify.order_action",
                data={
                    "private": (
                        "must not be projected"
                    ),
                },
            )
        ],
    )

    async with SessionLocal() as db:
        verification = await (
            TaskVerificationRepository(
                db
            ).append_attempt(
                user_id=user_id,
                request=request,
                result=result,
                idempotency_key=(
                    f"{verification_id}:1"
                ),
            )
        )
        await db.commit()
        await db.refresh(verification)

        event = await PlatformEventStore(
            db
        ).append(
            user_id=user_id,
            event_type=(
                TASK_VERIFICATION_COMPLETED_EVENT
            ),
            source=(
                "runtime.task_verification"
            ),
            payload={
                "record_id": str(
                    verification.id
                ),
                "verification_id": (
                    verification.verification_id
                ),
                "attempt_number": 1,
                "outcome": (
                    verification.outcome
                ),
            },
            meta={
                "tenant_id": (
                    verification.tenant_id
                ),
                "correlation_id": (
                    verification.correlation_id
                ),
            },
        )

        projector = (
            CapabilityLearningObservationProjector(
                db
            )
        )

        first = await projector.project_event(
            event
        )
        second = await projector.project_event(
            event
        )

        assert first["inserted"] is True
        assert second["inserted"] is False
        assert (
            first["learning_observation_id"]
            == second[
                "learning_observation_id"
            ]
        )

        row = await (
            CapabilityLearningObservationRepository(
                db
            ).get_by_verification_record(
                source_verification_record_id=(
                    verification.id
                )
            )
        )

        assert row is not None
        assert row.user_id == user_id
        assert row.outcome == (
            "partially_verified"
        )
        assert row.is_final is True
        assert row.retryable is False
        assert row.evidence_summary_json == {
            "count": 1,
            "items": [
                {
                    "kind": (
                        "execution_result"
                    ),
                    "source": (
                        "shopify.order_action"
                    ),
                    "observed_at_ts": (
                        result.evidence[
                            0
                        ].observed_at_ts
                    ),
                }
            ],
        }

        serialized = str(
            row.observation_json
        )

        assert (
            "private customer note"
            not in serialized
        )
        assert (
            "provider response"
            not in serialized
        )
        assert (
            "must not be projected"
            not in serialized
        )


@pytest.mark.asyncio
async def test_retryable_observation_is_non_final():
    user_id = uuid4()
    verification_id = (
        f"learning-retry-{uuid4()}"
    )

    request = TaskVerificationRequest(
        verification_id=verification_id,
        capability_id=(
            "ecommerce.orders.manage"
        ),
        provider_id="shopify",
        provider_ref="shopify.order_action",
        action="cancel",
        user_id=str(user_id),
    )

    result = TaskVerificationResult(
        verification_id=verification_id,
        capability_id=(
            request.capability_id
        ),
        provider_id="shopify",
        provider_ref="shopify.order_action",
        action="cancel",
        outcome=(
            TaskVerificationOutcome
            .INCONCLUSIVE
        ),
        method=(
            TaskVerificationMethod
            .REMOTE_STATE
        ),
        reason_code=(
            "provider_temporarily_unavailable"
        ),
        summary=(
            "Provider state could not be read."
        ),
        confidence=0.1,
        retryable=True,
        observed_outcome={},
        completed_at_ts=(
            datetime.now(
                timezone.utc
            ).timestamp()
        ),
    )

    async with SessionLocal() as db:
        verification = await (
            TaskVerificationRepository(
                db
            ).append_attempt(
                user_id=user_id,
                request=request,
                result=result,
                idempotency_key=(
                    f"{verification_id}:1"
                ),
            )
        )
        await db.commit()

        event = await PlatformEventStore(
            db
        ).append(
            user_id=user_id,
            event_type=(
                TASK_VERIFICATION_COMPLETED_EVENT
            ),
            source=(
                "runtime.task_verification"
            ),
            payload={
                "record_id": str(
                    verification.id
                ),
            },
            meta={},
        )

        projected = await (
            CapabilityLearningObservationProjector(
                db
            ).project_event(event)
        )

        assert projected["is_final"] is False

        row = await (
            CapabilityLearningObservationRepository(
                db
            ).get_by_verification_record(
                source_verification_record_id=(
                    verification.id
                )
            )
        )

        assert row is not None
        assert row.retryable is True
        assert row.is_final is False


@pytest.mark.asyncio
async def test_learning_queries_are_user_scoped():
    owner_id = uuid4()
    other_id = uuid4()
    verification_id = (
        f"learning-scope-{uuid4()}"
    )

    request = TaskVerificationRequest(
        verification_id=verification_id,
        capability_id=(
            "ecommerce.orders.manage"
        ),
        provider_id="shopify",
        action="refund",
        user_id=str(owner_id),
    )

    result = TaskVerificationResult(
        verification_id=verification_id,
        capability_id=(
            request.capability_id
        ),
        provider_id="shopify",
        action="refund",
        outcome=(
            TaskVerificationOutcome
            .VERIFIED
        ),
        method=(
            TaskVerificationMethod
            .REMOTE_STATE
        ),
        reason_code="verified",
        summary="Outcome verified.",
        confidence=1.0,
        retryable=False,
    )

    async with SessionLocal() as db:
        verification = await (
            TaskVerificationRepository(
                db
            ).append_attempt(
                user_id=owner_id,
                request=request,
                result=result,
                idempotency_key=(
                    f"{verification_id}:1"
                ),
            )
        )
        await db.commit()

        event = await PlatformEventStore(
            db
        ).append(
            user_id=owner_id,
            event_type=(
                TASK_VERIFICATION_COMPLETED_EVENT
            ),
            source=(
                "runtime.task_verification"
            ),
            payload={
                "record_id": str(
                    verification.id
                ),
            },
            meta={},
        )

        projected = await (
            CapabilityLearningObservationProjector(
                db
            ).project_event(event)
        )

        repository = (
            CapabilityLearningObservationRepository(
                db
            )
        )

        owner_row = await (
            repository.get_for_user(
                user_id=owner_id,
                record_id=projected[
                    "learning_observation_id"
                ],
            )
        )

        other_row = await (
            repository.get_for_user(
                user_id=other_id,
                record_id=projected[
                    "learning_observation_id"
                ],
            )
        )

        assert owner_row is not None
        assert other_row is None
