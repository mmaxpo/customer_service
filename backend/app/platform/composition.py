from __future__ import annotations


def register_default_event_handlers(
    registry,
) -> None:
    """
    Install Tajeran application reactions into an event registry.

    The generic event registry has no knowledge of Runtime,
    capabilities, or product domains.
    """

    from app.domains.customer_service.events.handlers import (
        register_customer_service_event_handlers,
    )
    from app.platform.events.handlers.capabilities import (
        register_capability_event_handlers,
    )
    from app.platform.events.handlers.waits import (
        register_wait_event_handlers,
    )
    from app.platform.events.handlers.workflow import (
        register_workflow_event_handlers,
    )

    register_workflow_event_handlers(registry)
    register_wait_event_handlers(registry)
    register_customer_service_event_handlers(registry)
    register_capability_event_handlers(registry)


def build_default_event_registry():
    """
    Build one fully composed Tajeran event registry.

    Composition happens at the infrastructure runtime boundary,
    never while the generic registry module is importing.
    """

    from app.platform.events.registry import (
        EventHandlerRegistry,
    )

    registry = EventHandlerRegistry()

    register_default_event_handlers(registry)

    return registry


def register_default_job_handlers(
    registry,
) -> None:
    """
    Install Tajeran application work into a job registry.

    Job infrastructure knows only how to execute registered work.
    Runtime, capability and domain modules contribute handlers.
    """

    from app.domains.customer_service.jobs.handlers import (
        register_customer_service_job_handlers,
    )
    from app.domains.customer_service.workflows.omnichannel_jobs import (
        register_customer_service_omnichannel_job_handlers,
    )
    from app.platform.jobs.handlers import (
        register_core_job_handlers,
    )
    from app.runtime.capabilities.execution.jobs import (
        register_capability_job_handlers,
    )
    from app.runtime.workflow_jobs import (
        register_workflow_job_handlers,
    )
    from app.tenancy.deletion import register_workspace_deletion_job_handlers

    register_core_job_handlers(registry)
    register_workflow_job_handlers(registry)
    register_customer_service_omnichannel_job_handlers(registry)
    register_customer_service_job_handlers(registry)
    register_capability_job_handlers(registry)
    register_workspace_deletion_job_handlers(registry)


def build_default_job_registry():
    """
    Build one fully composed Tajeran job registry.

    Import-time side effects are deliberately avoided.
    """

    from app.platform.jobs.handlers import (
        JobHandlerRegistry,
    )

    registry = JobHandlerRegistry()

    register_default_job_handlers(registry)

    return registry


__all__ = [
    "build_default_event_registry",
    "build_default_job_registry",
    "register_default_event_handlers",
    "register_default_job_handlers",
]


def build_default_webhook_provider_registry():
    """Build application webhook adapters at the composition boundary."""
    from app.domains.customer_service.integrations.shopify.webhooks import (
        ShopifyWebhookAdapter,
    )
    from app.platform.webhooks.providers.registry import (
        build_core_webhook_provider_registry,
    )
    from app.providers.stripe.webhooks import (
        StripeWebhookAdapter,
    )

    registry = build_core_webhook_provider_registry()

    registry.register(
        "shopify",
        ShopifyWebhookAdapter(),
    )

    registry.register(
        "stripe",
        StripeWebhookAdapter(),
    )

    return registry
