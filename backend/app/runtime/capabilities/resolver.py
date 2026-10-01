from __future__ import annotations
import time
from typing import Any
from fastapi import HTTPException
from app.integrations.errors import IntegrationError
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
    CapabilityRuntimePolicyReader,
    CapabilityRuntimePolicySnapshot,
    DatabaseProviderPerformanceScorer,
    DeterministicProviderTrafficAllocator,
    NullCapabilityRuntimePolicyReader,
    NullProviderHealthReader,
    NullProviderHealthProbeCoordinator,
    NullProviderInstallationReader,
    NullProviderPerformanceScorer,
    NullProviderTrafficAllocator,
    ProviderHealthProbeCoordinator,
    ProviderInstallationReader,
    ProviderInstallationSnapshot,
    ProviderPerformanceScorer,
    ProviderScoringResult,
    ProviderTrafficAllocator,
    ProviderHealthEnforcementMode,
    ProviderHealthReader,
    normalize_provider_health_enforcement_mode,
    build_default_executor_registry,
    classify_integration_failure,
)
from app.runtime.capabilities.execution.health.runtime import (
    ProviderHealthEnforcer,
)
from app.runtime.capabilities.execution.installation.enforcement import (
    ProviderInstallationEnforcer,
)
from app.runtime.capabilities.execution.runtime import (
    CapabilityExecutionRunner,
)

from app.runtime.capabilities.models import (
    CapabilityInvocation,
    CapabilityInvocationStatus,
    CapabilityResult,
)
from app.runtime.capabilities.registry import (
    CapabilityResolutionRequest,
    CapabilityResolutionResult,
    CapabilitySystem,
    RejectedProvider,
    build_default_system,
)


class CapabilityResolver:
    """
    Runtime execution bridge for the semantic capability system.

    Resolution and provider selection belong to CapabilitySystem. This class
    only translates runtime invocations, executes the selected provider
    reference, and returns the stable CapabilityResult contract.
    """

    def __init__(
        self,
        *,
        services: Any,
        system: CapabilitySystem | None = None,
        executor_registry: CapabilityExecutorRegistry | None = None,
        provider_health_reader: ProviderHealthReader | None = None,
        provider_health_probe_coordinator: (
            ProviderHealthProbeCoordinator | None
        ) = None,
        provider_health_probe_lease_seconds: int = 60,
        provider_health_probe_failure_cooldown_seconds: int = 300,
        provider_health_mode: (ProviderHealthEnforcementMode | str | None) = None,
        provider_performance_scorer: (
            ProviderPerformanceScorer | None
        ) = None,
        provider_traffic_allocator: (
            ProviderTrafficAllocator | None
        ) = None,
        capability_runtime_policy_reader: (
            CapabilityRuntimePolicyReader | None
        ) = None,
        provider_installation_reader: (
            ProviderInstallationReader | None
        ) = None,
        provider_performance_scorer_managed_by_policy: bool = False,
        provider_traffic_allocator_managed_by_policy: bool = False,
        registry: Any = None,
    ):
        self.services = services
        self.system = system or build_default_system()
        self.executor_registry = executor_registry or build_default_executor_registry()
        self.provider_health_reader = (
            provider_health_reader or NullProviderHealthReader()
        )
        self.provider_health_probe_coordinator = (
            provider_health_probe_coordinator or NullProviderHealthProbeCoordinator()
        )
        if provider_health_probe_lease_seconds < 1:
            raise ValueError("provider_health_probe_lease_seconds must be >= 1")
        self.provider_health_probe_lease_seconds = provider_health_probe_lease_seconds
        if provider_health_probe_failure_cooldown_seconds < 0:
            raise ValueError(
                "provider_health_probe_failure_cooldown_seconds must be >= 0"
            )
        self.provider_health_probe_failure_cooldown_seconds = (
            provider_health_probe_failure_cooldown_seconds
        )
        self.provider_health_mode = normalize_provider_health_enforcement_mode(
            provider_health_mode
        )
        self.provider_performance_scorer = (
            provider_performance_scorer
            or NullProviderPerformanceScorer()
        )
        self.provider_traffic_allocator = (
            provider_traffic_allocator
            or NullProviderTrafficAllocator()
        )
        self.capability_runtime_policy_reader = (
            capability_runtime_policy_reader
            or NullCapabilityRuntimePolicyReader()
        )
        self.provider_installation_reader = (
            provider_installation_reader
            or NullProviderInstallationReader()
        )
        self.provider_performance_scorer_managed_by_policy = bool(
            provider_performance_scorer_managed_by_policy
        )
        self.provider_traffic_allocator_managed_by_policy = bool(
            provider_traffic_allocator_managed_by_policy
        )

        # Retained temporarily for callers that still pass registry=. Runtime
        # execution no longer uses this registry for capability selection.
        self.registry = registry

        self._installation = ProviderInstallationEnforcer(
            services=self.services,
            system=self.system,
            reader=self.provider_installation_reader,
        )
        self._health = ProviderHealthEnforcer(
            services=self.services,
            system=self.system,
            reader=self.provider_health_reader,
            probe_coordinator=(
                self.provider_health_probe_coordinator
            ),
            mode=self.provider_health_mode,
            probe_lease_seconds=(
                self.provider_health_probe_lease_seconds
            ),
            probe_failure_cooldown_seconds=(
                self.provider_health_probe_failure_cooldown_seconds
            ),
        )
        self._execution = CapabilityExecutionRunner(
            services=self.services,
            system=self.system,
            executor_registry=self.executor_registry,
        )

    async def resolve(
        self,
        invocation: CapabilityInvocation,
    ) -> CapabilityResult:
        started = time.perf_counter()
        resolution: CapabilityResolutionResult | None = None
        attempts: list[dict[str, Any]] = []
        denied_provider_ids: set[str] = set()

        try:
            resolution = await self._resolve_provider_with_health(
                invocation=invocation,
                denied_provider_ids=(),
            )

            if not resolution.ok:
                return self._resolution_error_result(
                    invocation=invocation,
                    resolution=resolution,
                    started=started,
                    attempts=attempts,
                )

            while True:
                attempt_started = time.perf_counter()

                try:
                    output = await self._invoke_provider(
                        invocation=invocation,
                        resolution=resolution,
                    )
                except IntegrationError as exc:
                    failure = classify_integration_failure(exc)

                    attempts.append(
                        self._execution_attempt(
                            resolution=resolution,
                            outcome="error",
                            duration_ms=self._duration_ms(attempt_started),
                            error_code=failure.error_code,
                            error_message=failure.message,
                            failure_kind=failure.kind.value,
                            exception_type=failure.exception_type,
                            fallback_allowed=False,
                        )
                    )

                    fallback_allowed = self._can_fallback(
                        resolution=resolution,
                        failure_fallback_candidate=(failure.fallback_candidate),
                    )

                    attempts[-1]["fallback_allowed"] = fallback_allowed

                    if fallback_allowed:
                        selected_provider_id = resolution.selected_provider_id

                        if selected_provider_id:
                            denied_provider_ids.add(selected_provider_id)

                        next_resolution = await self._resolve_provider_with_health(
                            invocation=invocation,
                            denied_provider_ids=tuple(sorted(denied_provider_ids)),
                        )

                        if (
                            next_resolution.ok
                            and next_resolution.provider_ref
                            and self.executor_registry.has(next_resolution.provider_ref)
                        ):
                            resolution = next_resolution
                            continue

                        return self._integration_error_result(
                            invocation=invocation,
                            resolution=resolution,
                            started=started,
                            attempts=attempts,
                            error_code=failure.error_code,
                            error_message=failure.message,
                            failure_kind=failure.kind.value,
                            exception_type=failure.exception_type,
                            fallback_resolution=next_resolution,
                        )

                    return self._integration_error_result(
                        invocation=invocation,
                        resolution=resolution,
                        started=started,
                        attempts=attempts,
                        error_code=failure.error_code,
                        error_message=failure.message,
                        failure_kind=failure.kind.value,
                        exception_type=failure.exception_type,
                    )

                attempts.append(
                    self._execution_attempt(
                        resolution=resolution,
                        outcome="success",
                        duration_ms=self._duration_ms(attempt_started),
                    )
                )

                return CapabilityResult(
                    status=CapabilityInvocationStatus.OK,
                    capability_id=invocation.capability_id,
                    output=output,
                    duration_ms=self._duration_ms(started),
                    metadata=self._result_metadata(
                        invocation=invocation,
                        resolution=resolution,
                        extra={
                            "execution_attempts": attempts,
                            "fallback_used": len(attempts) > 1,
                        },
                    ),
                )

        except HTTPException as exc:
            return CapabilityResult(
                status=CapabilityInvocationStatus.ERROR,
                capability_id=invocation.capability_id,
                error_code=self._http_error_code(exc),
                error_message=str(exc.detail),
                duration_ms=self._duration_ms(started),
                metadata=self._result_metadata(
                    invocation=invocation,
                    resolution=resolution,
                    extra={
                        "http_status_code": exc.status_code,
                        "execution_attempts": attempts,
                        "fallback_used": False,
                    },
                ),
            )

        except KeyError as exc:
            missing_key = str(exc.args[0])

            return CapabilityResult(
                status=CapabilityInvocationStatus.ERROR,
                capability_id=invocation.capability_id,
                error_code="missing_required_input",
                error_message=(f"Missing required capability input: {missing_key}"),
                duration_ms=self._duration_ms(started),
                metadata=self._result_metadata(
                    invocation=invocation,
                    resolution=resolution,
                    extra={
                        "execution_attempts": attempts,
                        "fallback_used": False,
                    },
                ),
            )

        except ValueError as exc:
            return CapabilityResult(
                status=CapabilityInvocationStatus.ERROR,
                capability_id=invocation.capability_id,
                error_code=self._value_error_code(str(exc)),
                error_message=str(exc),
                duration_ms=self._duration_ms(started),
                metadata=self._result_metadata(
                    invocation=invocation,
                    resolution=resolution,
                    extra={
                        "execution_attempts": attempts,
                        "fallback_used": False,
                    },
                ),
            )

    def _resolve_provider(
        self,
        invocation: CapabilityInvocation,
        *,
        denied_provider_ids: tuple[str, ...] = (),
    ) -> CapabilityResolutionResult:
        tenant_id = getattr(
            getattr(self.services, "identity", None),
            "tenant_id",
            None,
        )
        resolved_user_id = invocation.user_id or getattr(
            getattr(self.services, "identity", None),
            "user_id",
            None,
        )

        action = invocation.inputs.get("action")

        preferred_provider_id = invocation.metadata.get(
            "preferred_provider_id"
        )

        return self.system.build_resolver().resolve(
            CapabilityResolutionRequest(
                capability_id=invocation.capability_id,
                user_id=(
                    str(resolved_user_id) if resolved_user_id is not None else None
                ),
                tenant_id=(str(tenant_id) if tenant_id is not None else None),
                preferred_provider_id=(
                    str(preferred_provider_id)
                    if preferred_provider_id is not None
                    else None
                ),
                inputs=invocation.inputs,
                context={
                    "correlation_id": invocation.correlation_id,
                    **invocation.metadata,
                },
                denied_provider_ids=denied_provider_ids,
                required_action=(str(action) if action is not None else None),
            )
        )

    async def _resolve_provider_with_health(
        self,
        *,
        invocation: CapabilityInvocation,
        denied_provider_ids: tuple[str, ...],
    ) -> CapabilityResolutionResult:
        """
        Resolve a provider and apply the configured scoped-health mode.

        Enforcement occurs before provider execution. In enforce mode, an
        effectively unhealthy provider is denied and semantic resolution is
        repeated. Reader failures and missing state remain fail-open.
        """

        denied = set(denied_provider_ids)
        health_rejections: list[RejectedProvider] = []

        (
            installation_rejections,
            installation_diagnostics,
        ) = await self._evaluate_provider_installations(
            invocation=invocation,
            denied_provider_ids=tuple(
                sorted(denied)
            ),
        )

        denied.update(
            item.provider_id
            for item in installation_rejections
        )

        def finalize_resolution(
            value: CapabilityResolutionResult,
        ) -> CapabilityResolutionResult:
            value = (
                self._merge_installation_rejections(
                    resolution=value,
                    installation_rejections=(
                        installation_rejections
                    ),
                    diagnostics=(
                        installation_diagnostics
                    ),
                )
            )

            return self._merge_health_rejections(
                resolution=value,
                health_rejections=health_rejections,
            )

        capability_policy = await self._resolve_runtime_policy(
            invocation=invocation,
        )

        (
            scoring,
            eligible_bindings,
        ) = await self._score_eligible_providers(
            invocation=invocation,
            denied_provider_ids=tuple(sorted(denied)),
            policy_snapshot=capability_policy,
        )
        allocation = self._allocate_provider_traffic(
            invocation=invocation,
            scoring=scoring,
            eligible_bindings=eligible_bindings,
            policy_snapshot=capability_policy,
        )
        scored_preferred_provider_id = (
            allocation.get("selected_provider_id")
            or scoring.get("selected_provider_id")
        )

        while True:
            scored_invocation = invocation

            if scored_preferred_provider_id:
                scored_invocation = invocation.model_copy(
                    update={
                        "metadata": {
                            **dict(invocation.metadata or {}),
                            "preferred_provider_id": (
                                scored_preferred_provider_id
                            ),
                        }
                    }
                )

            resolution = self._resolve_provider(
                scored_invocation,
                denied_provider_ids=tuple(sorted(denied)),
            )
            resolution = self._attach_provider_scoring_metadata(
                resolution=resolution,
                scoring=scoring,
            )
            resolution = self._attach_provider_allocation_metadata(
                resolution=resolution,
                allocation=allocation,
            )
            resolution = self._attach_runtime_policy_metadata(
                resolution=resolution,
                key="capability_runtime_policy",
                snapshot=capability_policy,
            )

            if not resolution.ok:
                return finalize_resolution(
                    resolution
                )

            provider_policy = await self._resolve_runtime_policy(
                invocation=invocation,
                provider_id=resolution.selected_provider_id,
                provider_ref=resolution.provider_ref,
            )
            resolution = self._attach_runtime_policy_metadata(
                resolution=resolution,
                key="provider_runtime_policy",
                snapshot=provider_policy,
            )

            resolution, should_reject = await self._apply_provider_health_mode(
                invocation=invocation,
                resolution=resolution,
                policy_snapshot=provider_policy,
            )

            if not should_reject:
                return finalize_resolution(
                    resolution
                )

            provider_id = resolution.selected_provider_id
            provider_ref = resolution.provider_ref
            health_metadata = resolution.metadata.get("provider_health") or {}

            if not provider_id:
                return finalize_resolution(
                    resolution
                )

            rejected_effective_state = health_metadata.get("effective_state")

            health_rejections.append(
                RejectedProvider(
                    provider_id=provider_id,
                    reason=(
                        "provider_recovering_scoped"
                        if rejected_effective_state == "recovering"
                        else "provider_unhealthy_scoped"
                    ),
                    metadata={
                        "provider_ref": provider_ref,
                        "effective_state": (health_metadata.get("effective_state")),
                        "current_state": (health_metadata.get("current_state")),
                        "override_active": (
                            health_metadata.get(
                                "override_active",
                                False,
                            )
                        ),
                        "state_version": (
                            health_metadata.get("state_version")
                        ),
                        "runtime_policy": (
                            resolution.metadata.get(
                                "provider_runtime_policy"
                            )
                        ),
                        "mode": (
                            (
                                resolution.metadata.get(
                                    "provider_runtime_policy"
                                )
                                or {}
                            )
                            .get("effective_policy", {})
                            .get(
                                "health_enforcement_mode",
                                self.provider_health_mode.value,
                            )
                        ),
                    },
                )
            )
            denied.add(provider_id)

            # A health-rejected scored provider cannot remain preferred on
            # the next semantic-resolution pass.
            if provider_id == scored_preferred_provider_id:
                scored_preferred_provider_id = None

    async def _evaluate_provider_installations(self, *, invocation: CapabilityInvocation, denied_provider_ids: tuple[str, ...]) -> tuple[list[RejectedProvider], list[dict[str, Any]]]:
        return await self._installation._evaluate_provider_installations(invocation=invocation, denied_provider_ids=denied_provider_ids)

    @staticmethod
    def _provider_installation_diagnostic(*, snapshot: ProviderInstallationSnapshot, provider_ref: str, rejection_reason: str | None, read_succeeded: bool) -> dict[str, Any]:
        return ProviderInstallationEnforcer._provider_installation_diagnostic(snapshot=snapshot, provider_ref=provider_ref, rejection_reason=rejection_reason, read_succeeded=read_succeeded)

    @staticmethod
    def _merge_installation_rejections(*, resolution: CapabilityResolutionResult, installation_rejections: list[RejectedProvider], diagnostics: list[dict[str, Any]]) -> CapabilityResolutionResult:
        return ProviderInstallationEnforcer._merge_installation_rejections(resolution=resolution, installation_rejections=installation_rejections, diagnostics=diagnostics)

    async def _score_eligible_providers(
        self,
        *,
        invocation: CapabilityInvocation,
        denied_provider_ids: tuple[str, ...],
        policy_snapshot: CapabilityRuntimePolicySnapshot | None = None,
    ) -> tuple[
        dict[str, Any],
        list[Any],
    ]:
        """
        Rank structurally eligible providers using durable observations.

        Eligibility remains owned by the synchronous semantic resolver. Each
        binding is resolved as an explicit preference so disabled, unauthenticated,
        disallowed, risky, region-incompatible, or otherwise invalid bindings
        never enter performance scoring.
        """

        capability_id = (
            self.system.aliases.resolve(invocation.capability_id)
            if self.system.aliases is not None
            else invocation.capability_id
        )

        if not self.system.capabilities.has_capability(
            capability_id
        ):
            return (
                {
                    "scoring_applied": False,
                    "fallback_to_priority": True,
                    "reason": "capability_not_registered",
                    "selected_provider_id": None,
                    "candidates": [],
                },
                [],
            )

        eligible_bindings = []

        for binding in self.system.bindings.list_for_capability(
            capability_id
        ):
            if binding.provider_id in denied_provider_ids:
                continue

            candidate_invocation = invocation.model_copy(
                update={
                    "metadata": {
                        **dict(invocation.metadata or {}),
                        "preferred_provider_id": (
                            binding.provider_id
                        ),
                    }
                }
            )
            candidate_resolution = self._resolve_provider(
                candidate_invocation,
                denied_provider_ids=denied_provider_ids,
            )

            if (
                candidate_resolution.ok
                and candidate_resolution.selected_provider_id
                == binding.provider_id
                and candidate_resolution.provider_ref
                == binding.provider_ref
            ):
                eligible_bindings.append(binding)

        tenant_id = getattr(
            getattr(self.services, "identity", None),
            "tenant_id",
            None,
        )
        resolved_user_id = invocation.user_id or getattr(
            getattr(self.services, "identity", None),
            "user_id",
            None,
        )

        scorer = self.provider_performance_scorer

        if (
            self.provider_performance_scorer_managed_by_policy
            and policy_snapshot is not None
            and getattr(self.services, "db", None) is not None
        ):
            policy = policy_snapshot.effective_policy
            scorer = DatabaseProviderPerformanceScorer(
                self.services.db,
                window_hours=policy.performance_window_hours,
                minimum_attempts=(
                    policy.minimum_performance_attempts
                ),
                priority_weight=policy.priority_weight,
                reliability_weight=policy.reliability_weight,
                latency_weight=policy.latency_weight,
            )

        try:
            result = await (
                scorer
                .score_candidates(
                    user_id=(
                        str(resolved_user_id)
                        if resolved_user_id is not None
                        else None
                    ),
                    tenant_id=(
                        str(tenant_id)
                        if tenant_id is not None
                        else None
                    ),
                    capability_id=capability_id,
                    candidates=eligible_bindings,
                )
            )
            return (
                result.model_dump(mode="json"),
                eligible_bindings,
            )
        except Exception as exc:
            ordered = sorted(
                eligible_bindings,
                key=lambda binding: (
                    -binding.priority,
                    binding.provider_id,
                    binding.provider_ref,
                ),
            )
            return (
                {
                    "scoring_applied": False,
                    "fallback_to_priority": True,
                    "reason": "provider_scoring_failed_open",
                    "selected_provider_id": (
                        ordered[0].provider_id
                        if ordered
                        else None
                    ),
                    "selected_provider_ref": (
                        ordered[0].provider_ref
                        if ordered
                        else None
                    ),
                    "candidates": [],
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
                eligible_bindings,
            )

    def _allocate_provider_traffic(
        self,
        *,
        invocation: CapabilityInvocation,
        scoring: dict[str, Any],
        eligible_bindings: list[Any],
        policy_snapshot: CapabilityRuntimePolicySnapshot | None = None,
    ) -> dict[str, Any]:
        capability_id = (
            self.system.aliases.resolve(
                invocation.capability_id
            )
            if self.system.aliases is not None
            else invocation.capability_id
        )

        if not self.system.capabilities.has_capability(
            capability_id
        ):
            return {
                "capability_id": capability_id,
                "allocation_applied": False,
                "reason": "capability_not_registered",
                "selected_provider_id": None,
                "selected_provider_ref": None,
                "candidates": [],
            }

        capability = (
            self.system.capabilities.get_capability(
                capability_id
            )
        )

        tenant_id = getattr(
            getattr(self.services, "identity", None),
            "tenant_id",
            None,
        )
        resolved_user_id = (
            invocation.user_id
            or getattr(
                getattr(
                    self.services,
                    "identity",
                    None,
                ),
                "user_id",
                None,
            )
        )

        allocator = self.provider_traffic_allocator

        if policy_snapshot is not None:
            policy = policy_snapshot.effective_policy

            if not policy.allocation_enabled:
                return {
                    "capability_id": capability_id,
                    "allocation_applied": False,
                    "reason": "disabled_by_runtime_policy",
                    "selected_provider_id": (
                        scoring.get("selected_provider_id")
                    ),
                    "selected_provider_ref": (
                        scoring.get("selected_provider_ref")
                    ),
                    "bucket_count": (
                        policy.allocation_bucket_count
                    ),
                    "competitive_margin": (
                        policy.competitive_allocation_margin
                    ),
                    "candidates": [],
                }

            if self.provider_traffic_allocator_managed_by_policy:
                allocator = DeterministicProviderTrafficAllocator(
                    competitive_margin=(
                        policy.competitive_allocation_margin
                    ),
                    bucket_count=(
                        policy.allocation_bucket_count
                    ),
                    maximum_candidates=(
                        policy.maximum_allocation_candidates
                    ),
                )

        try:
            result = allocator.allocate(
                user_id=(
                    str(resolved_user_id)
                    if resolved_user_id is not None
                    else None
                ),
                tenant_id=(
                    str(tenant_id)
                    if tenant_id is not None
                    else None
                ),
                capability_id=capability_id,
                correlation_id=invocation.correlation_id,
                capability_risk=capability.risk,
                bindings=eligible_bindings,
                scoring=(
                    ProviderScoringResult.model_validate(
                        scoring
                    )
                ),
            )
            return result.model_dump(mode="json")
        except Exception as exc:
            return {
                "capability_id": capability_id,
                "allocation_applied": False,
                "reason": (
                    "provider_allocation_failed_open"
                ),
                "selected_provider_id": (
                    scoring.get("selected_provider_id")
                ),
                "selected_provider_ref": (
                    scoring.get("selected_provider_ref")
                ),
                "candidates": [],
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

    async def _resolve_runtime_policy(
        self,
        *,
        invocation: CapabilityInvocation,
        provider_id: str | None = None,
        provider_ref: str | None = None,
    ) -> CapabilityRuntimePolicySnapshot:
        capability_id = (
            self.system.aliases.resolve(
                invocation.capability_id
            )
            if self.system.aliases is not None
            else invocation.capability_id
        )
        tenant_id = getattr(
            getattr(self.services, "identity", None),
            "tenant_id",
            None,
        )
        resolved_user_id = (
            invocation.user_id
            or getattr(
                getattr(self.services, "identity", None),
                "user_id",
                None,
            )
        )

        try:
            return await (
                self.capability_runtime_policy_reader
                .resolve_policy(
                    user_id=(
                        str(resolved_user_id)
                        if resolved_user_id is not None
                        else None
                    ),
                    tenant_id=(
                        str(tenant_id)
                        if tenant_id is not None
                        else None
                    ),
                    capability_id=capability_id,
                    provider_id=provider_id,
                    provider_ref=provider_ref,
                )
            )
        except Exception:
            return await (
                NullCapabilityRuntimePolicyReader()
                .resolve_policy(
                    user_id=(
                        str(resolved_user_id)
                        if resolved_user_id is not None
                        else None
                    ),
                    tenant_id=(
                        str(tenant_id)
                        if tenant_id is not None
                        else None
                    ),
                    capability_id=capability_id,
                    provider_id=provider_id,
                    provider_ref=provider_ref,
                )
            )

    @staticmethod
    def _attach_runtime_policy_metadata(
        *,
        resolution: CapabilityResolutionResult,
        key: str,
        snapshot: CapabilityRuntimePolicySnapshot,
    ) -> CapabilityResolutionResult:
        metadata = dict(resolution.metadata or {})
        policy_payload = snapshot.model_dump(mode="json")
        metadata[key] = policy_payload

        diagnostics = dict(
            metadata.get("diagnostics") or {}
        )
        diagnostic_metadata = dict(
            diagnostics.get("metadata") or {}
        )
        diagnostic_metadata[key] = policy_payload
        diagnostics["metadata"] = diagnostic_metadata
        metadata["diagnostics"] = diagnostics

        return resolution.model_copy(
            update={"metadata": metadata}
        )

    @staticmethod
    def _attach_provider_scoring_metadata(
        *,
        resolution: CapabilityResolutionResult,
        scoring: dict[str, Any],
    ) -> CapabilityResolutionResult:
        metadata = dict(resolution.metadata or {})
        metadata["provider_scoring"] = scoring

        diagnostics = dict(metadata.get("diagnostics") or {})
        diagnostic_metadata = dict(
            diagnostics.get("metadata") or {}
        )
        diagnostic_metadata["provider_scoring"] = scoring
        diagnostics["metadata"] = diagnostic_metadata
        metadata["diagnostics"] = diagnostics

        return resolution.model_copy(
            update={"metadata": metadata}
        )

    @staticmethod
    def _attach_provider_allocation_metadata(
        *,
        resolution: CapabilityResolutionResult,
        allocation: dict[str, Any],
    ) -> CapabilityResolutionResult:
        metadata = dict(resolution.metadata or {})
        metadata["provider_allocation"] = allocation

        diagnostics = dict(
            metadata.get("diagnostics") or {}
        )
        diagnostic_metadata = dict(
            diagnostics.get("metadata") or {}
        )
        diagnostic_metadata["provider_allocation"] = (
            allocation
        )
        diagnostics["metadata"] = diagnostic_metadata
        metadata["diagnostics"] = diagnostics

        return resolution.model_copy(
            update={"metadata": metadata}
        )

    async def _apply_provider_health_mode(self, *, invocation: CapabilityInvocation, resolution: CapabilityResolutionResult, policy_snapshot: CapabilityRuntimePolicySnapshot | None=None) -> tuple[CapabilityResolutionResult, bool]:
        return await self._health._apply_provider_health_mode(invocation=invocation, resolution=resolution, policy_snapshot=policy_snapshot)

    async def _try_health_probe(self, *, invocation: CapabilityInvocation, resolution: CapabilityResolutionResult, snapshot, lease_seconds: int | None=None) -> dict[str, Any]:
        return await self._health._try_health_probe(invocation=invocation, resolution=resolution, snapshot=snapshot, lease_seconds=lease_seconds)

    def _attach_health_metadata(self, *, resolution: CapabilityResolutionResult, diagnostic: dict[str, Any]) -> CapabilityResolutionResult:
        return self._health._attach_health_metadata(resolution=resolution, diagnostic=diagnostic)

    @staticmethod
    def _merge_health_rejections(*, resolution: CapabilityResolutionResult, health_rejections: list[RejectedProvider]) -> CapabilityResolutionResult:
        return ProviderHealthEnforcer._merge_health_rejections(resolution=resolution, health_rejections=health_rejections)

    async def _invoke_provider(self, *, invocation: CapabilityInvocation, resolution: CapabilityResolutionResult) -> Any:
        return await self._execution._invoke_provider(invocation=invocation, resolution=resolution)

    def _can_fallback(self, *, resolution: CapabilityResolutionResult, failure_fallback_candidate: bool) -> bool:
        return self._execution._can_fallback(resolution=resolution, failure_fallback_candidate=failure_fallback_candidate)

    @staticmethod
    def _execution_attempt(*, resolution: CapabilityResolutionResult, outcome: str, duration_ms: float, error_code: str | None=None, error_message: str | None=None, failure_kind: str | None=None, exception_type: str | None=None, fallback_allowed: bool=False) -> dict[str, Any]:
        return CapabilityExecutionRunner._execution_attempt(resolution=resolution, outcome=outcome, duration_ms=duration_ms, error_code=error_code, error_message=error_message, failure_kind=failure_kind, exception_type=exception_type, fallback_allowed=fallback_allowed)

    def _integration_error_result(self, *, invocation: CapabilityInvocation, resolution: CapabilityResolutionResult, started: float, attempts: list[dict[str, Any]], error_code: str, error_message: str, failure_kind: str, exception_type: str, fallback_resolution: CapabilityResolutionResult | None=None) -> CapabilityResult:
        return self._execution._integration_error_result(invocation=invocation, resolution=resolution, started=started, attempts=attempts, error_code=error_code, error_message=error_message, failure_kind=failure_kind, exception_type=exception_type, fallback_resolution=fallback_resolution)

    def _resolution_error_result(self, *, invocation: CapabilityInvocation, resolution: CapabilityResolutionResult, started: float, attempts: list[dict[str, Any]] | None=None) -> CapabilityResult:
        return self._execution._resolution_error_result(invocation=invocation, resolution=resolution, started=started, attempts=attempts)

    def _result_metadata(self, *, invocation: CapabilityInvocation, resolution: CapabilityResolutionResult | None, extra: dict[str, Any] | None=None) -> dict[str, Any]:
        return self._execution._result_metadata(invocation=invocation, resolution=resolution, extra=extra)

    @staticmethod
    def _duration_ms(started: float) -> float:
        return CapabilityExecutionRunner._duration_ms(started)

    @staticmethod
    def _http_error_code(exc: HTTPException) -> str:
        return CapabilityExecutionRunner._http_error_code(exc)

    @staticmethod
    def _value_error_code(message: str) -> str:
        return CapabilityExecutionRunner._value_error_code(message)

    async def invoke(
        self,
        capability_id: str,
        *,
        payload: dict[str, Any] | None = None,
        user_id: Any = None,
    ) -> Any:
        result = await self.resolve(
            CapabilityInvocation(
                capability_id=capability_id,
                inputs=payload or {},
                user_id=user_id,
            )
        )

        if not result.ok:
            raise ValueError(result.error_message or "Capability invocation failed")

        return result.output
