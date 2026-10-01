from __future__ import annotations

from uuid import UUID

from app.domains.customer_service.services.event_subscriptions import (
    CustomerServiceEventSubscriptionService,
)
from app.domains.customer_service.services.routing_engine.engine import (
    CustomerServiceRoutingEngine,
)
from app.domains.customer_service.workflows.trigger_handlers import (
    CustomerServiceWorkflowTriggerHandler,
)
from app.platform.jobs.service import JobService


async def handle_customer_service_omnichannel_message_received(event, ctx):
    if event.user_id is None:
        return {
            "skipped": True,
            "reason": "event has no user_id",
        }

    payload = event.payload or {}
    conversation_id = payload.get("conversation_id")
    body = payload.get("body")

    if not conversation_id or not body:
        return {
            "skipped": True,
            "reason": "event missing conversation_id or body",
        }

    workflow_result = await CustomerServiceWorkflowTriggerHandler(
        ctx.db,
    ).on_message_created(
        user_id=event.user_id,
        conversation_id=conversation_id,
        body=body,
    )

    payload = event.payload or {}
    classification = workflow_result.get("classification") or {}
    action = workflow_result.get("action") or {}

    routing_engine_result = await CustomerServiceRoutingEngine(
        ctx.db,
    ).route_conversation(
        user_id=event.user_id,
        conversation_id=payload.get("conversation_id"),
        channel=payload.get("channel"),
        body=payload.get("body") or "",
        intent=classification.get("intent"),
        priority=action.get("ticket_priority"),
    )

    if routing_engine_result is not None:
        routing_result = {
            "routed": True,
            "engine": {
                "policy_id": str(routing_engine_result["policy_id"]),
                "ticket_id": str(routing_engine_result["ticket_id"]),
                "assigned_to": str(routing_engine_result["assigned_to"]),
                "assignment_id": str(routing_engine_result["assignment_id"]),
            },
        }
    else:
        routing_result = {
            "routed": False,
            "reason": "no_matching_routing_policy",
        }

    subscription_result = await CustomerServiceEventSubscriptionService(
        ctx.db,
    ).enqueue_matching_workflows_for_event(
        event=event,
    )

    return {
        "handled": True,
        "workflow": workflow_result,
        "routing": routing_result,
        "subscriptions": subscription_result,
    }


SUPPORT_OUTCOME_RECORDED_EVENT = "customer_service.support.outcome.recorded"

CUSTOMER_SUPPORT_OUTCOME_EVALUATION_JOB = "customer_service.support_outcome.evaluate"


SUPPORT_OUTCOME_EVALUATED_EVENT = "customer_service.support.outcome.evaluated"

CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB = "customer_service.business_learning.project"

CUSTOMER_SUPPORT_OBJECTIVE_RESOLUTION_JOB = (
    "customer_service.objective_resolution.project"
)

OBJECTIVE_RESOLUTION_ASSESSED_EVENT = "runtime.objective.resolution.assessed"

CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB = "customer_service.objective_learning.record"


async def enqueue_customer_support_outcome_evaluation(
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
    raw_outcome_id = payload.get("outcome_id")

    if not raw_outcome_id:
        return {
            "scheduled": False,
            "reason": ("support_outcome_id_missing"),
            "source_event_id": str(event.id),
        }

    evaluation_version = 1

    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type=(CUSTOMER_SUPPORT_OUTCOME_EVALUATION_JOB),
        payload={
            "source_event_id": str(event.id),
            "support_outcome_id": str(raw_outcome_id),
            "evaluation_version": (evaluation_version),
        },
        max_attempts=5,
        idempotency_key=(
            "customer-support-outcome-evaluation:"
            f"{raw_outcome_id}:"
            f"v{evaluation_version}"
        ),
        commit=False,
    )

    return {
        "scheduled": True,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "support_outcome_id": str(raw_outcome_id),
        "evaluation_version": (evaluation_version),
        "source_event_id": str(event.id),
    }


async def enqueue_customer_support_business_learning(
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

    raw_evaluation_id = payload.get("evaluation_id")
    raw_outcome_id = payload.get("support_outcome_id")

    if not raw_evaluation_id:
        return {
            "scheduled": False,
            "reason": "evaluation_id_missing",
            "source_event_id": str(event.id),
        }

    if not raw_outcome_id:
        return {
            "scheduled": False,
            "reason": ("support_outcome_id_missing"),
            "source_event_id": str(event.id),
        }

    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type=(CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB),
        payload={
            "source_event_id": str(event.id),
            "evaluation_id": str(raw_evaluation_id),
            "support_outcome_id": str(raw_outcome_id),
        },
        max_attempts=5,
        idempotency_key=(f"customer-support-business-learning:{raw_evaluation_id}"),
        commit=False,
    )

    return {
        "scheduled": True,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "source_event_id": str(event.id),
        "evaluation_id": str(raw_evaluation_id),
        "support_outcome_id": str(raw_outcome_id),
    }


async def enqueue_customer_support_objective_resolution(
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

    raw_evaluation_id = payload.get("evaluation_id")
    raw_outcome_id = payload.get("support_outcome_id")

    if not raw_evaluation_id:
        return {
            "scheduled": False,
            "reason": "evaluation_id_missing",
            "source_event_id": str(event.id),
        }

    if not raw_outcome_id:
        return {
            "scheduled": False,
            "reason": ("support_outcome_id_missing"),
            "source_event_id": str(event.id),
        }

    projection_version = 1
    evaluation_version = int(payload.get("evaluation_version") or 1)

    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type=(CUSTOMER_SUPPORT_OBJECTIVE_RESOLUTION_JOB),
        payload={
            "source_event_id": str(event.id),
            "evaluation_id": str(raw_evaluation_id),
            "support_outcome_id": str(raw_outcome_id),
            "evaluation_version": (evaluation_version),
            "projection_version": (projection_version),
        },
        max_attempts=5,
        idempotency_key=(
            "customer-support-objective-resolution:"
            f"{raw_evaluation_id}:"
            f"e{evaluation_version}:"
            f"p{projection_version}"
        ),
        commit=False,
    )

    return {
        "scheduled": True,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "source_event_id": str(event.id),
        "evaluation_id": str(raw_evaluation_id),
        "support_outcome_id": str(raw_outcome_id),
        "evaluation_version": (evaluation_version),
        "projection_version": (projection_version),
    }


async def enqueue_customer_support_objective_learning(
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
    raw_resolution_record_id = payload.get("resolution_record_id")

    if not raw_resolution_record_id:
        return {
            "scheduled": False,
            "reason": "resolution_record_id_missing",
            "source_event_id": str(event.id),
        }

    try:
        resolution_record_id = UUID(str(raw_resolution_record_id))
    except ValueError:
        return {
            "scheduled": False,
            "reason": "resolution_record_id_invalid",
            "source_event_id": str(event.id),
        }

    if payload.get("is_terminal") is not True:
        return {
            "scheduled": False,
            "reason": "resolution_is_not_terminal",
            "source_event_id": str(event.id),
            "resolution_record_id": str(resolution_record_id),
        }

    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB),
        payload={
            "source_event_id": str(event.id),
            "resolution_record_id": str(resolution_record_id),
        },
        max_attempts=5,
        idempotency_key=(f"customer-support-objective-learning:{resolution_record_id}"),
        commit=False,
    )

    return {
        "scheduled": True,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "source_event_id": str(event.id),
        "resolution_record_id": str(resolution_record_id),
    }


CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_PLANNED_EVENT = "runtime.objective.repair.planned"

CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB = (
    "customer_service.objective_repair.launch"
)


async def enqueue_customer_support_objective_repair_launch(
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
    raw_repair_execution_id = payload.get("repair_execution_id")

    if not raw_repair_execution_id:
        return {
            "scheduled": False,
            "reason": "repair_execution_id_missing",
            "source_event_id": str(event.id),
        }

    try:
        repair_execution_id = UUID(str(raw_repair_execution_id))
    except ValueError:
        return {
            "scheduled": False,
            "reason": "repair_execution_id_invalid",
            "source_event_id": str(event.id),
        }

    # Lazy import is required. Importing JobService through the
    # repair service graph at module load time creates a cycle
    # through PlatformEventPublisher/EventHandlerRegistry.
    from app.platform.jobs.service import JobService

    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type=(CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB),
        payload={
            "source_event_id": str(event.id),
            "repair_execution_id": str(repair_execution_id),
        },
        max_attempts=5,
        idempotency_key=(
            f"customer-support-objective-repair-launch:{repair_execution_id}"
        ),
        commit=False,
    )

    return {
        "scheduled": True,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "repair_execution_id": str(repair_execution_id),
        "source_event_id": str(event.id),
    }


async def project_customer_support_repair_job_succeeded(
    event,
    ctx,
):
    return await _project_customer_support_repair_job_event(
        event=event,
        ctx=ctx,
        event_kind="succeeded",
    )


async def project_customer_support_repair_job_failed(
    event,
    ctx,
):
    payload = dict(event.payload or {})

    if str(payload.get("status") or "") != "queued":
        return {
            "projected": False,
            "reason": "job_failure_is_not_retryable",
            "source_event_id": str(event.id),
        }

    return await _project_customer_support_repair_job_event(
        event=event,
        ctx=ctx,
        event_kind="retryable_failed",
    )


async def project_customer_support_repair_job_dead_lettered(
    event,
    ctx,
):
    return await _project_customer_support_repair_job_event(
        event=event,
        ctx=ctx,
        event_kind="dead_lettered",
    )


async def _project_customer_support_repair_job_event(
    *,
    event,
    ctx,
    event_kind: str,
):
    if event.user_id is None:
        return {
            "projected": False,
            "reason": "event_user_id_missing",
            "source_event_id": str(event.id),
        }

    payload = dict(event.payload or {})
    job_type = str(payload.get("job_type") or "").strip()

    if job_type not in {
        "workflow.run",
        "workflow.resume",
    }:
        return {
            "projected": False,
            "reason": "job_type_not_supported",
            "source_event_id": str(event.id),
        }

    raw_job_id = payload.get("job_id")

    if not raw_job_id:
        return {
            "projected": False,
            "reason": "job_id_missing",
            "source_event_id": str(event.id),
        }

    try:
        workflow_job_id = UUID(str(raw_job_id))
    except ValueError:
        return {
            "projected": False,
            "reason": "job_id_invalid",
            "source_event_id": str(event.id),
        }

    # Lazy import prevents:
    # event registry -> customer_service handler -> projector
    # -> objective repair service -> event publisher -> registry.
    from app.domains.customer_service.services.support.repair.lifecycle_projection import (
        CustomerSupportRepairLifecycleProjector,
    )

    projector = CustomerSupportRepairLifecycleProjector(ctx.db)

    if event_kind == "succeeded":
        projection = await projector.project_succeeded_job(
            user_id=event.user_id,
            workflow_job_id=workflow_job_id,
        )
    elif event_kind == "retryable_failed":
        projection = await projector.project_retryable_failed_job(
            user_id=event.user_id,
            workflow_job_id=workflow_job_id,
        )
    elif event_kind == "dead_lettered":
        projection = await projector.project_dead_lettered_job(
            user_id=event.user_id,
            workflow_job_id=workflow_job_id,
            error_message=payload.get("error_message"),
        )
    else:
        raise ValueError(f"Unsupported repair projection event: {event_kind}")

    return {
        "projected": projection.projected,
        "reason": projection.reason,
        "workflow_job_id": str(projection.workflow_job_id),
        "repair_execution_id": (
            str(projection.repair_execution.id)
            if projection.repair_execution is not None
            else None
        ),
        "source_event_id": str(event.id),
    }


async def publish_customer_service_workflow_job_realtime(
    event,
    ctx,
):
    """
    Project generic platform job lifecycle events into
    customer-service realtime semantics.

    JobWorker owns only generic job lifecycle mechanics.
    Customer Service decides whether a workflow job means
    anything to its realtime clients.
    """

    payload = dict(event.payload or {})

    job_type = str(payload.get("job_type") or "").strip()

    if job_type not in {
        "workflow.run",
        "workflow.resume",
    }:
        return {
            "published": False,
            "reason": "job_type_not_supported",
            "source_event_id": str(event.id),
        }

    raw_job_id = payload.get("job_id")

    if not raw_job_id:
        return {
            "published": False,
            "reason": "job_id_missing",
            "source_event_id": str(event.id),
        }

    try:
        job_id = UUID(str(raw_job_id))
    except ValueError:
        return {
            "published": False,
            "reason": "job_id_invalid",
            "source_event_id": str(event.id),
        }

    from app.platform.jobs.repository import (
        JobRepository,
    )

    job = await JobRepository(ctx.db).get(job_id)

    if job is None:
        return {
            "published": False,
            "reason": "job_not_found",
            "source_event_id": str(event.id),
        }

    job_payload = job.payload or {}
    extras = job_payload.get("extras") or {}

    if not extras.get("customer_service"):
        return {
            "published": False,
            "reason": "not_customer_service",
            "source_event_id": str(event.id),
        }

    event_payload = (extras.get("event") or {}).get("payload") or {}

    conversation_id = event_payload.get("conversation_id")

    result = (
        job.result
        if isinstance(
            job.result,
            dict,
        )
        else {}
    )

    meta = result.get("meta") or {}

    workflow_run_id = (
        result.get("workflow_run_id")
        or result.get("run_id")
        or meta.get("workflow_run_id")
    )

    realtime_payload = {
        "job_type": job.job_type,
        "job_status": job.status,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "ticket_id": event_payload.get("ticket_id"),
        "customer_id": event_payload.get("customer_id"),
        "message": job_payload.get("message"),
        "workflow_status": meta.get("status"),
        "error_message": (job.error_message),
    }

    from app.domains.customer_service.realtime.publisher import (
        CustomerServiceRealtimePublisher,
    )

    publisher = CustomerServiceRealtimePublisher()

    status = str(job.status)

    if status == "succeeded":
        workflow_status = str(meta.get("status") or "").lower()

        if workflow_status == "paused":
            await publisher.publish_workflow_paused(
                user_id=job.user_id,
                conversation_id=conversation_id,
                job_id=job.id,
                workflow_run_id=workflow_run_id,
                payload=realtime_payload,
            )

            interrupt = result.get("interrupt") or meta.get("interrupt") or {}

            wait_type = (
                interrupt.get("wait_type")
                or interrupt.get("kind")
                or interrupt.get("node_type")
                or meta.get("wait_type")
            )

            if "approval" in str(wait_type).lower():
                await publisher.publish_approval_required(
                    user_id=job.user_id,
                    conversation_id=conversation_id,
                    job_id=job.id,
                    workflow_run_id=workflow_run_id,
                    payload={
                        **realtime_payload,
                        "interrupt": interrupt,
                    },
                )
                from app.domains.customer_service.services.notifications import (
                    NotificationService,
                )

                await NotificationService(ctx.db).create_for_roles(
                    workspace_id=job.user_id,
                    roles={"owner", "admin"},
                    kind="approval",
                    entity_type="workflow_job",
                    entity_id=job.id,
                    payload={
                        "conversation_id": str(conversation_id)
                        if conversation_id
                        else None,
                        "workflow_run_id": str(workflow_run_id)
                        if workflow_run_id
                        else None,
                        "interrupt": interrupt,
                    },
                )

            return {
                "published": True,
                "kind": "paused",
                "source_event_id": str(event.id),
            }

        await publisher.publish_workflow_succeeded(
            user_id=job.user_id,
            conversation_id=conversation_id,
            job_id=job.id,
            workflow_run_id=workflow_run_id,
            payload=realtime_payload,
        )

        return {
            "published": True,
            "kind": "succeeded",
            "source_event_id": str(event.id),
        }

    if status in {
        "failed",
        "dead_letter",
    }:
        await publisher.publish_workflow_failed(
            user_id=job.user_id,
            conversation_id=conversation_id,
            job_id=job.id,
            workflow_run_id=workflow_run_id,
            payload=realtime_payload,
        )

        return {
            "published": True,
            "kind": "failed",
            "source_event_id": str(event.id),
        }

    # Retryable job failures return to queued state.
    # The old JobWorker logic intentionally emitted no
    # customer-service realtime failure for those attempts.
    return {
        "published": False,
        "reason": "job_status_not_realtime_terminal",
        "source_event_id": str(event.id),
    }


DEAD_LETTER_SAFE_REPLY = (
    "Thanks for your message. A member of our team will get back to you shortly."
)


async def send_customer_chat_safe_reply_on_dead_letter(
    event,
    ctx,
):
    """A chat workflow failed on every attempt: tell the customer a person will reply."""
    payload = dict(event.payload or {})

    if str(payload.get("job_type") or "") != "workflow.run" or not payload.get(
        "job_id"
    ):
        return {"sent": False, "reason": "job_type_not_supported"}

    from app.platform.jobs.repository import JobRepository

    job = await JobRepository(ctx.db).get(UUID(str(payload["job_id"])))
    extras = ((job.payload or {}).get("extras") or {}) if job is not None else {}
    session_id = ((extras.get("event") or {}).get("payload") or {}).get("session_id")

    if not extras.get("customer_service") or not session_id:
        return {"sent": False, "reason": "not_customer_chat"}

    from app.domains.customer_service.repositories.chat_repository import (
        ChatRepository,
    )
    from app.domains.customer_service.services.chat_service import (
        CustomerChatService,
    )

    service = CustomerChatService(ChatRepository(ctx.db))
    session = await service.get_session(session_id=UUID(str(session_id)))

    if session is None or str(session.user_id) != str(job.user_id):
        return {"sent": False, "reason": "session_not_found"}

    # One safe reply per failed job, even if the event is delivered twice.
    client_message_id = f"dead-letter:{job.id}"
    existing = await service.repository.get_message_by_client_message_id(
        session_id=session.id,
        client_message_id=client_message_id,
    )

    if existing is not None:
        return {"sent": False, "reason": "already_sent"}

    chat_message = await service.add_ai_message(
        session_id=session.id,
        content=DEAD_LETTER_SAFE_REPLY,
        client_message_id=client_message_id,
    )
    await service.add_inbox_ai_message_for_chat_session(
        session=session,
        chat_message=chat_message,
    )
    await ctx.db.commit()

    return {"sent": True, "chat_message_id": str(chat_message.id)}


def register_customer_service_event_handlers(registry) -> None:
    registry.subscribe(
        "customer_service.omnichannel.message.received",
        handle_customer_service_omnichannel_message_received,
    )
    registry.subscribe(
        SUPPORT_OUTCOME_RECORDED_EVENT,
        enqueue_customer_support_outcome_evaluation,
    )
    registry.subscribe(
        SUPPORT_OUTCOME_EVALUATED_EVENT,
        enqueue_customer_support_business_learning,
    )
    registry.subscribe(
        SUPPORT_OUTCOME_EVALUATED_EVENT,
        enqueue_customer_support_objective_resolution,
    )
    registry.subscribe(
        OBJECTIVE_RESOLUTION_ASSESSED_EVENT,
        enqueue_customer_support_objective_learning,
    )
    registry.subscribe(
        CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_PLANNED_EVENT,
        enqueue_customer_support_objective_repair_launch,
    )
    registry.subscribe(
        "job.succeeded",
        project_customer_support_repair_job_succeeded,
    )
    registry.subscribe(
        "job.succeeded",
        publish_customer_service_workflow_job_realtime,
    )
    registry.subscribe(
        "job.failed",
        project_customer_support_repair_job_failed,
    )
    registry.subscribe(
        "job.failed",
        publish_customer_service_workflow_job_realtime,
    )
    registry.subscribe(
        "job.dead_lettered",
        project_customer_support_repair_job_dead_lettered,
    )
    registry.subscribe(
        "job.dead_lettered",
        send_customer_chat_safe_reply_on_dead_letter,
    )
