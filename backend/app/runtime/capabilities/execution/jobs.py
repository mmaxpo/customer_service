from __future__ import annotations

from uuid import UUID

from app.platform.events.event_store import PlatformEventStore
from app.runtime.capabilities.execution.health.evaluation import (
    CapabilityHealthEvaluationRequest,
    CapabilityHealthEvaluationService,
)
from app.runtime.capabilities.execution.health.reconciler import (
    CapabilityHealthEvaluationReconciler,
    CapabilityHealthReconcileRequest,
)
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningObservationProjector,
)
from app.runtime.capabilities.execution.performance.projection import (
    DurableCapabilityPerformanceProjector,
)
from app.runtime.capabilities.execution.performance.repository import (
    CapabilityPerformanceObservationRepository,
)
from app.runtime.capabilities.execution.verification import (
    TaskVerificationRequest,
)
from app.runtime_services import build_application_runtime_services


async def verify_capability_task_job(
    payload,
    ctx,
):
    raw_event_id = payload.get("source_event_id")

    if not raw_event_id:
        raise ValueError("source_event_id is required")

    event_id = UUID(str(raw_event_id))
    event = await PlatformEventStore(ctx.db).get(event_id)

    if event is None:
        raise ValueError(f"Platform event not found: {event_id}")

    if event.user_id is None:
        raise ValueError("Capability event user_id is required")

    if ctx.job.user_id is not None and UUID(str(ctx.job.user_id)) != UUID(
        str(event.user_id)
    ):
        raise ValueError(
            "Task verification event ownership does not match job ownership"
        )

    event_payload = dict(event.payload or {})
    event_meta = dict(event.meta or {})

    if not bool(event_payload.get("ok")):
        return {
            "status": "skipped",
            "reason": ("capability_execution_not_successful"),
            "source_event_id": str(event.id),
        }

    verification_context = event_payload.get("verification_context")

    if not isinstance(
        verification_context,
        dict,
    ):
        return {
            "status": "skipped",
            "reason": ("capability_not_automatically_verifiable"),
            "source_event_id": str(event.id),
        }

    invocation_metadata = dict(event_meta.get("invocation_metadata") or {})

    verification_id = f"capability-event:{event.id}"

    request = TaskVerificationRequest(
        verification_id=verification_id,
        capability_id=(
            event_payload.get("resolved_capability_id")
            or event_payload["requested_capability_id"]
        ),
        provider_id=(event_payload.get("selected_provider_id")),
        provider_ref=(event_payload.get("provider_ref")),
        action=verification_context.get("action"),
        user_id=str(event.user_id),
        tenant_id=(
            str(event_meta["tenant_id"])
            if event_meta.get("tenant_id") is not None
            else None
        ),
        correlation_id=(event_meta.get("correlation_id") or str(event.id)),
        workflow_run_id=(
            event_meta.get("workflow_run_id")
            or invocation_metadata.get("workflow_run_id")
        ),
        task_id=(
            invocation_metadata.get("task_id") or invocation_metadata.get("node_id")
        ),
        inputs=dict(verification_context.get("inputs") or {}),
        expected_outcome=dict(verification_context.get("expected_outcome") or {}),
        execution_output=(verification_context.get("execution_output")),
        metadata={
            "automatic": True,
            "source_event_id": str(event.id),
            "source_event_type": (event.event_type),
        },
    )

    services = build_application_runtime_services(
        db=ctx.db,
        user_id=event.user_id,
        tenant_id=request.tenant_id,
    )

    execution = await services.task_verification.verify(
        user_id=event.user_id,
        request=request,
        idempotency_key=(f"{verification_id}:attempt:1"),
    )

    return {
        "status": "verified",
        "source_event_id": str(event.id),
        "verification_id": (execution.result.verification_id),
        "record_id": execution.record_id,
        "attempt_number": (execution.attempt_number),
        "created": execution.created,
        "outcome": (execution.result.outcome.value),
        "retryable": (execution.result.retryable),
    }


async def project_capability_performance_job(
    payload,
    ctx,
):
    raw_event_id = payload.get("source_event_id")

    if not raw_event_id:
        raise ValueError("source_event_id is required")

    event_id = UUID(str(raw_event_id))
    event = await PlatformEventStore(ctx.db).get(event_id)

    if event is None:
        raise ValueError(f"Platform event not found: {event_id}")

    return await DurableCapabilityPerformanceProjector(
        repository=CapabilityPerformanceObservationRepository(ctx.db)
    ).project_event(event)


async def project_capability_learning_job(
    payload,
    ctx,
):
    raw_event_id = payload.get("source_event_id")

    if not raw_event_id:
        raise ValueError("source_event_id is required")

    event_id = UUID(str(raw_event_id))
    event = await PlatformEventStore(ctx.db).get(event_id)

    if event is None:
        raise ValueError(f"Platform event not found: {event_id}")

    if event.user_id is None:
        raise ValueError("Task verification event user_id is required")

    if ctx.job.user_id is not None and UUID(str(ctx.job.user_id)) != UUID(
        str(event.user_id)
    ):
        raise ValueError(
            "Learning projection event ownership does not match job ownership"
        )

    return await CapabilityLearningObservationProjector(ctx.db).project_event(event)


async def reconcile_capability_health_job(
    payload,
    ctx,
):
    request = CapabilityHealthReconcileRequest.model_validate(payload)

    return await CapabilityHealthEvaluationReconciler(ctx.db).reconcile(request=request)


async def evaluate_capability_health_job(
    payload,
    ctx,
):
    request = CapabilityHealthEvaluationRequest.model_validate(payload)

    if ctx.job.user_id is not None:
        job_user_id = UUID(str(ctx.job.user_id))

        if request.user_id != job_user_id:
            raise ValueError(
                "Health evaluation payload user_id does not match job ownership"
            )

    return await CapabilityHealthEvaluationService(ctx.db).evaluate(request=request)


def register_capability_job_handlers(registry) -> None:
    registry.register(
        "capability.performance.project",
        project_capability_performance_job,
    )
    registry.register(
        "capability.task.verify",
        verify_capability_task_job,
    )
    registry.register(
        "capability.learning.project",
        project_capability_learning_job,
    )
    registry.register(
        "capability.health.evaluate",
        evaluate_capability_health_job,
    )
    registry.register(
        "capability.health.reconcile",
        reconcile_capability_health_job,
    )


__all__ = [
    "project_capability_learning_job",
    "evaluate_capability_health_job",
    "reconcile_capability_health_job",
    "project_capability_performance_job",
    "verify_capability_task_job",
    "register_capability_job_handlers",
]
