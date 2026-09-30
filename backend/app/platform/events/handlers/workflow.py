from app.platform.jobs.service import JobService


async def enqueue_workflow_from_event(event, ctx):
    workflow = event.payload.get("workflow")
    workflow_id = event.payload.get("workflow_id")

    if not workflow and not workflow_id:
        return {
            "skipped": True,
            "reason": "No workflow or workflow_id in event payload",
        }

    job_payload = {
        **event.payload,
        "event": {
            "id": str(event.id),
            "event_type": event.event_type,
            "source": event.source,
            "payload": event.payload,
            "meta": event.meta,
        },
    }

    job = await JobService(ctx.db).enqueue(
        user_id=event.user_id,
        job_type="workflow.run",
        payload=job_payload,
        max_attempts=3,
    )

    return {
        "enqueued_job_id": str(job.id),
        "job_type": job.job_type,
    }


def register_workflow_event_handlers(registry):
    registry.subscribe("workflow.requested", enqueue_workflow_from_event)
