from __future__ import annotations

from app.platform.jobs.service import JobService

CAPABILITY_EXECUTION_COMPLETED_EVENT = "runtime.capability.execution.completed"

TASK_VERIFICATION_COMPLETED_EVENT = "runtime.task.verification.completed"


CAPABILITY_PERFORMANCE_PROJECTION_JOB = "capability.performance.project"

CAPABILITY_TASK_VERIFICATION_JOB = "capability.task.verify"


CAPABILITY_LEARNING_PROJECTION_JOB = "capability.learning.project"


async def enqueue_capability_performance_projection(
    event,
    ctx,
):
    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type=CAPABILITY_PERFORMANCE_PROJECTION_JOB,
        payload={
            "source_event_id": str(event.id),
        },
        max_attempts=5,
    )

    return {
        "enqueued_job_id": str(job.id),
        "job_type": job.job_type,
        "source_event_id": str(event.id),
    }


async def enqueue_capability_task_verification(
    event,
    ctx,
):
    payload = dict(event.payload or {})
    verification_context = payload.get("verification_context")

    if not bool(payload.get("ok")):
        return {
            "scheduled": False,
            "reason": ("capability_execution_not_successful"),
        }

    if not isinstance(
        verification_context,
        dict,
    ):
        return {
            "scheduled": False,
            "reason": ("capability_not_automatically_verifiable"),
        }

    if event.user_id is None:
        return {
            "scheduled": False,
            "reason": "event_user_id_missing",
        }

    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type=(CAPABILITY_TASK_VERIFICATION_JOB),
        payload={
            "source_event_id": str(event.id),
        },
        max_attempts=5,
        idempotency_key=(f"capability-task-verification:{event.id}"),
    )

    return {
        "scheduled": True,
        "enqueued_job_id": str(job.id),
        "job_type": job.job_type,
        "source_event_id": str(event.id),
    }


async def enqueue_capability_learning_projection(
    event,
    ctx,
):
    if event.user_id is None:
        return {
            "scheduled": False,
            "reason": "event_user_id_missing",
            "source_event_id": str(event.id),
        }

    payload = dict(event.payload or {})

    if not payload.get("record_id"):
        return {
            "scheduled": False,
            "reason": ("verification_record_id_missing"),
            "source_event_id": str(event.id),
        }

    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type=(CAPABILITY_LEARNING_PROJECTION_JOB),
        payload={
            "source_event_id": str(event.id),
        },
        max_attempts=5,
        idempotency_key=(f"capability-learning-projection:{event.id}"),
    )

    return {
        "scheduled": True,
        "enqueued_job_id": str(job.id),
        "job_type": job.job_type,
        "source_event_id": str(event.id),
    }


def register_capability_event_handlers(registry) -> None:
    registry.subscribe(
        CAPABILITY_EXECUTION_COMPLETED_EVENT,
        enqueue_capability_performance_projection,
    )
    registry.subscribe(
        CAPABILITY_EXECUTION_COMPLETED_EVENT,
        enqueue_capability_task_verification,
    )
    registry.subscribe(
        TASK_VERIFICATION_COMPLETED_EVENT,
        enqueue_capability_learning_projection,
    )


__all__ = [
    "enqueue_capability_learning_projection",
    "CAPABILITY_LEARNING_PROJECTION_JOB",
    "CAPABILITY_PERFORMANCE_PROJECTION_JOB",
    "CAPABILITY_TASK_VERIFICATION_JOB",
    "enqueue_capability_performance_projection",
    "enqueue_capability_task_verification",
    "register_capability_event_handlers",
]
