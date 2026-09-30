from __future__ import annotations

from uuid import UUID

from app.domains.customer_service.services.support.learning.customer_support_business_learning_projection import (
    CustomerSupportBusinessLearningProjector,
)
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_recording import (
    CustomerSupportObjectiveLearningRecordingService,
)
from app.domains.customer_service.services.support.outcome.customer_support_outcome_evaluation_service import (
    CustomerSupportOutcomeEvaluationService,
)
from app.domains.customer_service.services.support.repair.launch import (
    CustomerSupportRepairLaunchCoordinator,
)
from app.domains.customer_service.services.support.resolution.customer_support_resolution_projection import (
    CUSTOMER_SUPPORT_RESOLUTION_PROJECTION_VERSION,
    CustomerSupportResolutionProjector,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)

CUSTOMER_SUPPORT_OUTCOME_EVALUATION_JOB = "customer_service.support_outcome.evaluate"
CUSTOMER_SERVICE_CONVERSATION_WAKE_JOB = "customer_service.conversation.wake"
CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB = "customer_service.reply_draft.scheduled"
CUSTOMER_SERVICE_PROACTIVE_EVALUATION_JOB = "customer_service.proactive.evaluate"


CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB = "customer_service.business_learning.project"

CUSTOMER_SUPPORT_OBJECTIVE_RESOLUTION_JOB = (
    "customer_service.objective_resolution.project"
)

CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB = "customer_service.objective_learning.record"

OBJECTIVE_RESOLUTION_ASSESSED_EVENT = "runtime.objective.resolution.assessed"

CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB = (
    "customer_service.objective_repair.launch"
)

SUPPORT_OUTCOME_EVALUATED_EVENT = "customer_service.support.outcome.evaluated"

SUPPORT_OUTCOME_RECORDED_EVENT = "customer_service.support.outcome.recorded"


async def evaluate_customer_support_outcome_job(
    payload,
    ctx,
):
    raw_event_id = payload.get("source_event_id")
    raw_outcome_id = payload.get("support_outcome_id")
    evaluation_version = int(payload.get("evaluation_version") or 1)

    if not raw_event_id:
        raise ValueError("source_event_id is required")

    if not raw_outcome_id:
        raise ValueError("support_outcome_id is required")

    if evaluation_version != 1:
        raise ValueError(
            "Unsupported customer support outcome "
            f"evaluation version: "
            f"{evaluation_version}"
        )

    event_id = UUID(str(raw_event_id))
    support_outcome_id = UUID(str(raw_outcome_id))

    event = await PlatformEventStore(ctx.db).get(event_id)

    if event is None:
        raise ValueError(f"Support outcome source event not found: {event_id}")

    if event.event_type != SUPPORT_OUTCOME_RECORDED_EVENT:
        raise ValueError(
            f"Unexpected support outcome source event type: {event.event_type}"
        )

    if event.user_id is None:
        raise ValueError("Support outcome event user_id is required")

    event_user_id = UUID(str(event.user_id))

    if ctx.job.user_id is not None and UUID(str(ctx.job.user_id)) != event_user_id:
        raise ValueError(
            "Support outcome evaluation event ownership does not match job ownership"
        )

    event_outcome_id = dict(event.payload or {}).get("outcome_id")

    if not event_outcome_id or UUID(str(event_outcome_id)) != support_outcome_id:
        raise ValueError(
            "Support outcome evaluation payload does not match source event"
        )

    execution = await CustomerSupportOutcomeEvaluationService(ctx.db).evaluate(
        user_id=event_user_id,
        support_outcome_id=(support_outcome_id),
    )

    return {
        "status": "evaluated",
        "source_event_id": str(event.id),
        "support_outcome_id": str(support_outcome_id),
        "evaluation_id": str(execution.record.id),
        "evaluation_version": (execution.record.evaluation_version),
        "result": execution.record.result,
        "reason_code": (execution.record.reason_code),
        "created": execution.created,
        "event_id": (
            str(execution.event_id) if execution.event_id is not None else None
        ),
    }


async def project_customer_support_business_learning_job(
    payload,
    ctx,
):
    raw_event_id = payload.get("source_event_id")
    raw_evaluation_id = payload.get("evaluation_id")
    raw_outcome_id = payload.get("support_outcome_id")

    if not raw_event_id:
        raise ValueError("source_event_id is required")

    if not raw_evaluation_id:
        raise ValueError("evaluation_id is required")

    if not raw_outcome_id:
        raise ValueError("support_outcome_id is required")

    event_id = UUID(str(raw_event_id))
    evaluation_id = UUID(str(raw_evaluation_id))
    outcome_id = UUID(str(raw_outcome_id))

    event = await PlatformEventStore(ctx.db).get(event_id)

    if event is None:
        raise ValueError(f"Business learning source event not found: {event_id}")

    if event.event_type != SUPPORT_OUTCOME_EVALUATED_EVENT:
        raise ValueError(
            f"Unexpected business learning source event type: {event.event_type}"
        )

    if event.user_id is None:
        raise ValueError("Business learning event user_id is required")

    event_user_id = UUID(str(event.user_id))

    if ctx.job.user_id is not None and UUID(str(ctx.job.user_id)) != event_user_id:
        raise ValueError(
            "Business learning event ownership does not match job ownership"
        )

    event_payload = dict(event.payload or {})

    if UUID(str(event_payload.get("evaluation_id"))) != evaluation_id:
        raise ValueError(
            "Business learning evaluation identity does not match source event"
        )

    if UUID(str(event_payload.get("support_outcome_id"))) != outcome_id:
        raise ValueError(
            "Business learning outcome identity does not match source event"
        )

    return await CustomerSupportBusinessLearningProjector(ctx.db).project_event(event)


async def project_customer_support_objective_resolution_job(
    payload,
    ctx,
):
    raw_event_id = payload.get("source_event_id")
    raw_evaluation_id = payload.get("evaluation_id")
    raw_outcome_id = payload.get("support_outcome_id")

    evaluation_version = int(payload.get("evaluation_version") or 1)
    projection_version = int(payload.get("projection_version") or 1)

    if not raw_event_id:
        raise ValueError("source_event_id is required")

    if not raw_evaluation_id:
        raise ValueError("evaluation_id is required")

    if not raw_outcome_id:
        raise ValueError("support_outcome_id is required")

    if evaluation_version != 1:
        raise ValueError(
            "Unsupported customer support outcome "
            "evaluation version: "
            f"{evaluation_version}"
        )

    if projection_version != CUSTOMER_SUPPORT_RESOLUTION_PROJECTION_VERSION:
        raise ValueError(
            "Unsupported customer support objective "
            "resolution projection version: "
            f"{projection_version}"
        )

    event_id = UUID(str(raw_event_id))
    evaluation_id = UUID(str(raw_evaluation_id))
    outcome_id = UUID(str(raw_outcome_id))

    event = await PlatformEventStore(ctx.db).get(event_id)

    if event is None:
        raise ValueError(f"Objective-resolution source event not found: {event_id}")

    if event.event_type != SUPPORT_OUTCOME_EVALUATED_EVENT:
        raise ValueError(
            f"Unexpected objective-resolution source event type: {event.event_type}"
        )

    if event.user_id is None:
        raise ValueError("Objective-resolution event user_id is required")

    event_user_id = UUID(str(event.user_id))

    if ctx.job.user_id is not None and UUID(str(ctx.job.user_id)) != event_user_id:
        raise ValueError(
            "Objective-resolution event ownership does not match job ownership"
        )

    event_payload = dict(event.payload or {})

    if UUID(str(event_payload.get("evaluation_id"))) != evaluation_id:
        raise ValueError(
            "Objective-resolution evaluation identity does not match source event"
        )

    if UUID(str(event_payload.get("support_outcome_id"))) != outcome_id:
        raise ValueError(
            "Objective-resolution outcome identity does not match source event"
        )

    event_evaluation_version = int(event_payload.get("evaluation_version") or 1)

    if event_evaluation_version != evaluation_version:
        raise ValueError(
            "Objective-resolution evaluation version does not match source event"
        )

    execution = await CustomerSupportResolutionProjector(ctx.db).project_event(
        event,
        projection_version=(projection_version),
    )

    return {
        "status": "projected",
        "source_event_id": str(event.id),
        "evaluation_id": str(evaluation_id),
        "support_outcome_id": str(outcome_id),
        "resolution_record_id": str(execution.record.id),
        "projection_version": (execution.record.projection_version),
        "objective_namespace": (execution.record.objective_namespace),
        "objective_ref": (execution.record.objective_ref),
        "resolution_status": (execution.record.status),
        "is_terminal": (execution.record.is_terminal),
        "created": execution.created,
        "event_id": (
            str(execution.event_id) if execution.event_id is not None else None
        ),
    }


async def record_customer_support_objective_learning_job(
    payload,
    ctx,
):
    raw_event_id = payload.get("source_event_id")
    raw_resolution_record_id = payload.get("resolution_record_id")

    if not raw_event_id:
        raise ValueError("source_event_id is required")

    if not raw_resolution_record_id:
        raise ValueError("resolution_record_id is required")

    event_id = UUID(str(raw_event_id))
    resolution_record_id = UUID(str(raw_resolution_record_id))

    event = await PlatformEventStore(ctx.db).get(event_id)

    if event is None:
        raise ValueError(f"Objective-learning source event not found: {event_id}")

    if event.event_type != OBJECTIVE_RESOLUTION_ASSESSED_EVENT:
        raise ValueError(
            f"Unexpected objective-learning source event type: {event.event_type}"
        )

    if event.user_id is None:
        raise ValueError("Objective-learning event user_id is required")

    event_user_id = UUID(str(event.user_id))

    if ctx.job.user_id is not None and UUID(str(ctx.job.user_id)) != event_user_id:
        raise ValueError(
            "Objective-learning event ownership does not match job ownership"
        )

    event_payload = dict(event.payload or {})
    raw_event_resolution_record_id = event_payload.get("resolution_record_id")

    if (
        not raw_event_resolution_record_id
        or UUID(str(raw_event_resolution_record_id)) != resolution_record_id
    ):
        raise ValueError(
            "Objective-learning resolution identity does not match source event"
        )

    if event_payload.get("is_terminal") is not True:
        raise ValueError("Objective-learning source resolution must be terminal")

    tenant_id = None
    event_meta = dict(event.meta or {})

    if event_meta.get("tenant_id") is not None:
        normalized_tenant = str(event_meta["tenant_id"]).strip()
        tenant_id = normalized_tenant if normalized_tenant else None

    result = await CustomerSupportObjectiveLearningRecordingService(
        ctx.db
    ).record_for_resolution(
        user_id=event_user_id,
        resolution_record_id=(resolution_record_id),
        tenant_id=tenant_id,
    )

    return {
        "status": "recorded",
        "source_event_id": str(event.id),
        "resolution_record_id": str(resolution_record_id),
        "learning_experience_id": str(result.record.id),
        "profile_ref": (result.record.profile_ref),
        "profile_version": (result.record.profile_version),
        "created": result.created,
        "informational_only": (result.record.informational_only),
        "authorizes_execution": (result.record.authorizes_execution),
    }


async def launch_customer_support_objective_repair_job(
    payload,
    ctx,
):
    raw_repair_execution_id = payload.get("repair_execution_id")

    if not raw_repair_execution_id:
        raise ValueError("repair_execution_id is required")

    if ctx.job.user_id is None:
        raise ValueError("Customer-support repair launch job requires user_id")

    try:
        repair_execution_id = UUID(str(raw_repair_execution_id))
    except ValueError as exc:
        raise ValueError("repair_execution_id must be a valid UUID") from exc

    result = await CustomerSupportRepairLaunchCoordinator(ctx.db).launch(
        user_id=ctx.job.user_id,
        repair_execution_id=(repair_execution_id),
    )

    return {
        "repair_execution_id": str(result.repair_execution.id),
        "repair_status": (result.repair_execution.status),
        "workflow_job_id": str(result.workflow_job.id),
        "workflow_job_type": (result.workflow_job.job_type),
        "controlling_disposition": (result.repair_execution.controlling_disposition),
        "already_queued": (result.already_queued),
    }


def register_customer_service_job_handlers(
    registry,
) -> None:
    registry.register(
        CUSTOMER_SUPPORT_OUTCOME_EVALUATION_JOB,
        evaluate_customer_support_outcome_job,
    )
    registry.register(
        CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB,
        project_customer_support_business_learning_job,
    )
    registry.register(
        CUSTOMER_SUPPORT_OBJECTIVE_RESOLUTION_JOB,
        project_customer_support_objective_resolution_job,
    )
    registry.register(
        CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB,
        record_customer_support_objective_learning_job,
    )
    registry.register(
        CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB,
        launch_customer_support_objective_repair_job,
    )
    registry.register(
        "customer_service.privacy.process",
        process_customer_service_privacy_request_job,
    )
    registry.register(
        CUSTOMER_SERVICE_CONVERSATION_WAKE_JOB,
        wake_customer_service_conversation_job,
    )
    registry.register(
        CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
        process_customer_service_scheduled_reply_job,
    )
    registry.register(
        CUSTOMER_SERVICE_PROACTIVE_EVALUATION_JOB,
        evaluate_customer_service_proactive_playbooks_job,
    )


async def process_customer_service_privacy_request_job(payload, ctx):
    from app.domains.customer_service.services.commercial_operations import (
        CommercialOperationsService,
    )

    if ctx.job.user_id is None:
        raise ValueError("Privacy request job requires workspace user_id")
    request_id = UUID(str(payload["request_id"]))
    row = await CommercialOperationsService(
        ctx.db,
        workspace_id=ctx.job.user_id,
    ).process_privacy_request(request_id)
    return {
        "request_id": str(row.id),
        "status": row.status,
        "kind": row.kind,
    }


async def process_customer_service_scheduled_reply_job(payload, ctx):
    from app.domains.customer_service.services.helpdesk import (
        CustomerServiceHelpdeskService,
    )

    if ctx.job.user_id is None:
        raise ValueError("Scheduled reply job requires workspace user_id")

    raw_actor_user_id = payload.get("scheduled_by_user_id")

    if not raw_actor_user_id:
        raise ValueError("Scheduled reply job requires scheduled_by_user_id")

    return await CustomerServiceHelpdeskService(
        ctx.db,
        workspace_id=ctx.job.user_id,
        actor_user_id=UUID(str(raw_actor_user_id)),
    ).execute_scheduled_draft_trigger(
        draft_id=UUID(str(payload["draft_id"])),
        expected_version=int(payload["expected_version"]),
        expected_scheduled_for=str(payload["expected_scheduled_for"]),
    )


async def wake_customer_service_conversation_job(payload, ctx):
    from app.domains.customer_service.services.helpdesk import (
        CustomerServiceHelpdeskService,
    )

    if ctx.job.user_id is None:
        raise ValueError("Conversation wake job requires workspace user_id")
    conversation_id = UUID(str(payload["conversation_id"]))
    return await CustomerServiceHelpdeskService(
        ctx.db,
        workspace_id=ctx.job.user_id,
        actor_user_id=ctx.job.user_id,
    ).wake(
        conversation_id,
        expected_until=payload.get("expected_snoozed_until"),
    )


async def evaluate_customer_service_proactive_playbooks_job(payload, ctx):
    from app.domains.customer_service.services.proactive_playbooks import (
        CustomerServiceProactivePlaybookService,
    )

    raw_workspace_id = payload.get("workspace_id")
    if not raw_workspace_id or ctx.job.user_id is None:
        raise ValueError("Proactive evaluation job requires workspace_id")
    workspace_id = UUID(str(raw_workspace_id))
    if UUID(str(ctx.job.user_id)) != workspace_id:
        raise ValueError("Proactive evaluation workspace does not match job ownership")
    return await CustomerServiceProactivePlaybookService(
        ctx.db, workspace_id=workspace_id
    ).evaluate()


__all__ = [
    "CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB",
    "CUSTOMER_SERVICE_CONVERSATION_WAKE_JOB",
    "CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB",
    "CUSTOMER_SERVICE_PROACTIVE_EVALUATION_JOB",
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB",
    "CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB",
    "CUSTOMER_SUPPORT_OBJECTIVE_RESOLUTION_JOB",
    "project_customer_support_business_learning_job",
    "launch_customer_support_objective_repair_job",
    "project_customer_support_objective_resolution_job",
    "record_customer_support_objective_learning_job",
    "CUSTOMER_SUPPORT_OUTCOME_EVALUATION_JOB",
    "evaluate_customer_support_outcome_job",
    "register_customer_service_job_handlers",
    "process_customer_service_privacy_request_job",
    "wake_customer_service_conversation_job",
    "process_customer_service_scheduled_reply_job",
    "evaluate_customer_service_proactive_playbooks_job",
]
