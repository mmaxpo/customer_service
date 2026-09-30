from __future__ import annotations

from typing import Any

from app.core.session import SessionLocal
from app.runtime.resources.models import (
    AIServices,
    BusinessServices,
    DataServices,
    IdentityServices,
    InfrastructureServices,
    RuntimeKernelServices,
    RuntimeServices,
)
from app.runtime.capabilities.invoker import CapabilityInvoker
from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    DatabaseCapabilityRuntimePolicyReader,
    DatabaseProviderHealthReader,
    DatabaseProviderInstallationReader,
    DatabaseProviderPerformanceScorer,
    DeterministicProviderTrafficAllocator,
    IsolatedDatabaseProviderHealthProbeCoordinator,
    NullCapabilityOutcomeReporter,
    NullCapabilityRuntimePolicyReader,
    NullProviderHealthReader,
    NullProviderInstallationReader,
    CapabilityRuntimePolicyReader,
    ProviderHealthReader,
    ProviderHealthEnforcementMode,
    ProviderInstallationReader,
    ProviderTrafficAllocator,
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


class RuntimeServiceFactory:
    @staticmethod
    def build(
        *,
        request: Any = None,
        db: Any = None,
        tools: Any = None,
        user_id: Any = None,
        tenant_id: Any = None,
        thread_id: Any = None,
        run_store: Any = None,
        event_sink: Any = None,
        extras: dict[str, Any] | None = None,
        business: BusinessServices | None = None,
        capability_outcome_reporter: Any = None,
        provider_health_mode: (
            ProviderHealthEnforcementMode | str | None
        ) = None,
    ) -> RuntimeServices:
        resolved_tools = tools
        if resolved_tools is None and request is not None:
            resolved_tools = getattr(getattr(request, "state", None), "tools", None)

        capability_system = build_default_system()
        capability_executors = build_default_executor_registry()
        provider_health_reader: ProviderHealthReader = (
            DatabaseProviderHealthReader(db)
            if db is not None
            else NullProviderHealthReader()
        )
        provider_health_probe_coordinator = (
            IsolatedDatabaseProviderHealthProbeCoordinator(
                SessionLocal
            )
            if db is not None
            else None
        )
        provider_performance_scorer = (
            DatabaseProviderPerformanceScorer(db)
            if db is not None
            else None
        )
        provider_traffic_allocator: ProviderTrafficAllocator = (
            DeterministicProviderTrafficAllocator()
        )
        capability_runtime_policy_reader: CapabilityRuntimePolicyReader = (
            DatabaseCapabilityRuntimePolicyReader(db)
            if db is not None
            else NullCapabilityRuntimePolicyReader()
        )
        provider_installation_reader: ProviderInstallationReader = (
            DatabaseProviderInstallationReader(db)
            if db is not None
            else NullProviderInstallationReader()
        )
        resolved_outcome_reporter = (
            capability_outcome_reporter
            or NullCapabilityOutcomeReporter()
        )

        validate_executor_coverage(
            system=capability_system,
            executors=capability_executors,
        ).require_complete()

        services = RuntimeServices(
            identity=IdentityServices(
                user_id=user_id,
                tenant_id=tenant_id,
                thread_id=thread_id,
            ),
            data=DataServices(
                db=db,
            ),
            ai=AIServices(
                tools=resolved_tools,
                llm=getattr(resolved_tools, "llm", None)
                if resolved_tools is not None
                else None,
                agent_llm=getattr(resolved_tools, "agent_llm", None)
                if resolved_tools is not None
                else None,
            ),
            business=(
                business
                if business is not None
                else BusinessServices()
            ),
            runtime=RuntimeKernelServices(
                run_store=run_store,
            ),
            infrastructure=InfrastructureServices(
                event_sink=event_sink,
            ),
        )
        services.capability_system = capability_system
        services.capability_registry = capability_system.capabilities
        services.capability_executors = capability_executors
        services.capability_outcome_reporter = (
            resolved_outcome_reporter
        )
        services.task_verifiers = (
            build_default_task_verifier_registry()
        )
        services.task_verification = (
            TaskVerificationService(
                db,
                services=services,
                registry=services.task_verifiers,
            )
            if db is not None
            else None
        )
        services.provider_health_mode = (
            provider_health_mode
            or ProviderHealthEnforcementMode.SHADOW
        )
        services.capabilities = CapabilityInvoker(
            resolver=CapabilityResolver(
                services=services,
                system=capability_system,
                executor_registry=capability_executors,
                provider_health_reader=provider_health_reader,
                provider_health_probe_coordinator=(
                    provider_health_probe_coordinator
                ),
                provider_health_mode=(
                    services.provider_health_mode
                ),
                provider_performance_scorer=(
                    provider_performance_scorer
                ),
                provider_traffic_allocator=(
                    provider_traffic_allocator
                ),
                capability_runtime_policy_reader=(
                    capability_runtime_policy_reader
                ),
                provider_installation_reader=(
                    provider_installation_reader
                ),
                provider_performance_scorer_managed_by_policy=(
                    db is not None
                ),
                provider_traffic_allocator_managed_by_policy=True,
            ),
            outcome_reporter=resolved_outcome_reporter,
        )
        return services
