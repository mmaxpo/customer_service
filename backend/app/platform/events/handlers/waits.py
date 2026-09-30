from app.workflow_operations.waits.event_resolver import WorkflowWaitEventResolver


async def resolve_workflow_waits_from_event(event, ctx):
    resolved = await WorkflowWaitEventResolver(ctx.db).resolve_for_event(
        event=event,
    )

    return {
        "resolved_wait_ids": [str(wait.id) for wait in resolved],
        "resolved_count": len(resolved),
    }


def register_wait_event_handlers(registry):
    registry.subscribe("*", resolve_workflow_waits_from_event)
