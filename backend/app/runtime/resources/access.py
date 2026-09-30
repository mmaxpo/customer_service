from __future__ import annotations

from typing import Any

from app.core.session import SessionLocal
from app.runtime.resources.models import RuntimeServices
from app.runtime.resources.build import RuntimeServiceFactory
from app.runtime.capabilities.invoker import CapabilityInvoker
from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    ProviderInstallationReader,
    ProviderHealthReader,
    DatabaseProviderHealthReader,
    DatabaseProviderInstallationReader,
    IsolatedDatabaseProviderHealthProbeCoordinator,
    NullCapabilityOutcomeReporter,
    NullProviderHealthReader,
    NullProviderInstallationReader,
    ProviderHealthEnforcementMode,
    build_default_executor_registry,
    validate_executor_coverage,
)
from app.runtime.capabilities.execution.verification import (
    TaskVerificationService,
    build_default_task_verifier_registry,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


def get_runtime_services(ctx: Any) -> RuntimeServices:
    services = getattr(ctx, "services", None)

    fallback_db = getattr(ctx, "db", None)
    fallback_tools = getattr(ctx, "tools", None)
    fallback_user_id = getattr(ctx, "user_id", None)
    fallback_tenant_id = getattr(ctx, "tenant_id", None)
    fallback_thread_id = getattr(ctx, "thread_id", None)
    fallback_run_store = getattr(ctx, "run_store", None)
    fallback_event_sink = getattr(ctx, "event_sink", None)
    fallback_request = getattr(ctx, "request", None)

    if services is not None:
        if getattr(services.data, "db", None) is None and fallback_db is not None:
            services.data.db = fallback_db
        if getattr(services.ai, "tools", None) is None and fallback_tools is not None:
            services.ai.tools = fallback_tools
        if (
            getattr(services.identity, "user_id", None) is None
            and fallback_user_id is not None
        ):
            services.identity.user_id = fallback_user_id
        if (
            getattr(services.identity, "tenant_id", None) is None
            and fallback_tenant_id is not None
        ):
            services.identity.tenant_id = fallback_tenant_id
        if (
            getattr(services.identity, "thread_id", None) is None
            and fallback_thread_id is not None
        ):
            services.identity.thread_id = fallback_thread_id
        if (
            getattr(services.runtime, "run_store", None) is None
            and fallback_run_store is not None
        ):
            services.runtime.run_store = fallback_run_store
        if (
            getattr(services.infrastructure, "event_sink", None) is None
            and fallback_event_sink is not None
        ):
            services.infrastructure.event_sink = fallback_event_sink
        if getattr(services, "capability_system", None) is None:
            services.capability_system = build_default_system()

        if getattr(services, "capability_registry", None) is None:
            services.capability_registry = (
                services.capability_system.capabilities
            )

        if getattr(services, "capability_executors", None) is None:
            services.capability_executors = (
                build_default_executor_registry()
            )

        validate_executor_coverage(
            system=services.capability_system,
            executors=services.capability_executors,
        ).require_complete()

        if getattr(
            services,
            "capability_outcome_reporter",
            None,
        ) is None:
            services.capability_outcome_reporter = (
                NullCapabilityOutcomeReporter()
            )

        if getattr(
            services,
            "task_verifiers",
            None,
        ) is None:
            services.task_verifiers = (
                build_default_task_verifier_registry()
            )

        if (
            getattr(
                services,
                "task_verification",
                None,
            )
            is None
            and services.data.db is not None
        ):
            services.task_verification = (
                TaskVerificationService(
                    services.data.db,
                    services=services,
                    registry=(
                        services.task_verifiers
                    ),
                )
            )

        if getattr(services, "capabilities", None) is None:
            provider_health_reader: ProviderHealthReader = (
                DatabaseProviderHealthReader(
                    services.data.db
                )
                if services.data.db is not None
                else NullProviderHealthReader()
            )

            provider_installation_reader: ProviderInstallationReader = (
                DatabaseProviderInstallationReader(
                    services.data.db
                )
                if services.data.db is not None
                else NullProviderInstallationReader()
            )

            provider_health_probe_coordinator = (
                IsolatedDatabaseProviderHealthProbeCoordinator(
                    SessionLocal
                )
                if services.data.db is not None
                else None
            )

            services.capabilities = CapabilityInvoker(
                resolver=CapabilityResolver(
                    services=services,
                    system=services.capability_system,
                    executor_registry=services.capability_executors,
                    provider_health_reader=provider_health_reader,
                    provider_health_probe_coordinator=(
                        provider_health_probe_coordinator
                    ),
                    provider_installation_reader=(
                        provider_installation_reader
                    ),
                    provider_health_mode=getattr(
                        services,
                        "provider_health_mode",
                        ProviderHealthEnforcementMode.SHADOW,
                    ),
                ),
                outcome_reporter=(
                    services.capability_outcome_reporter
                ),
            )
        return services

    return RuntimeServiceFactory.build(
        request=fallback_request,
        db=fallback_db,
        tools=fallback_tools,
        user_id=fallback_user_id,
        tenant_id=fallback_tenant_id,
        thread_id=fallback_thread_id,
        run_store=fallback_run_store,
        event_sink=fallback_event_sink,
    )
