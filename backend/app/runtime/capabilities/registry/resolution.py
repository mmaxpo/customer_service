from __future__ import annotations
from dataclasses import dataclass, field
from app.runtime.capabilities.registry.policies import ResolverPolicy
from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.registries import CapabilityAliasRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.state import TenantProviderRegistry
from app.runtime.capabilities.registry.state import ProviderAuthRegistry
from app.runtime.capabilities.registry.state import ProviderHealthRegistry
from app.runtime.capabilities.registry.policies import (
    SelectionPolicy,
    ResolutionContext,
    BindingEnabledPolicy,
    TenantAvailabilityPolicy,
    ProviderHealthPolicy,
    ProviderAuthPolicy,
    CostPolicy,
    LatencyPolicy,
    RiskPolicy,
    ApprovalPolicy,
    AllowDenyPolicy,
    RegionPolicy,
    CapabilityConstraintPolicy,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    CapabilityResolutionResult,
    RejectedProvider,
)

"""
Canonical capability-resolution implementation.

This module owns:
- ResolverPipeline
- CapabilityResolver
- the stable resolution public API

Individual policy implementations remain isolated under policies/ because each
policy has one focused responsibility.

"""




@dataclass
class ResolverPipeline:
    policies: list[ResolverPolicy] = field(default_factory=list)

    def run(self, ctx) -> None:
        for policy in self.policies:
            policy.apply(ctx)





def _diagnostics(
    *,
    status: str,
    requested_capability_id: str,
    resolved_capability_id: str,
    selected_provider_id: str | None = None,
    provider_ref: str | None = None,
    runtime_node_type: str | None = None,
    missing_inputs: tuple[str, ...] = (),
    rejected_providers: tuple[RejectedProvider, ...] = (),
    metadata: dict | None = None,
) -> dict:
    return {
        "status": status,
        "requested_capability_id": requested_capability_id,
        "resolved_capability_id": resolved_capability_id,
        "selected_provider_id": selected_provider_id,
        "provider_ref": provider_ref,
        "runtime_node_type": runtime_node_type,
        "missing_inputs": list(missing_inputs),
        "rejected_providers": [
            item.model_dump(mode="json") for item in rejected_providers
        ],
        "metadata": metadata or {},
    }

@dataclass
class CapabilityResolver:
    capabilities: CapabilityRegistry
    providers: ProviderRegistry
    bindings: BindingRegistry
    aliases: CapabilityAliasRegistry | None = None
    tenant_providers: TenantProviderRegistry | None = None
    provider_auth: ProviderAuthRegistry | None = None
    provider_health: ProviderHealthRegistry | None = None

    def _build_pipeline(self) -> ResolverPipeline:
        return ResolverPipeline(
            policies=[
                BindingEnabledPolicy(),
                TenantAvailabilityPolicy(self.tenant_providers),
                ProviderHealthPolicy(self.provider_health),
                ProviderAuthPolicy(
                    providers=self.providers,
                    provider_auth=self.provider_auth,
                ),
                CostPolicy(),
                LatencyPolicy(),
                RiskPolicy(),
                ApprovalPolicy(),
                AllowDenyPolicy(),
                RegionPolicy(),
                CapabilityConstraintPolicy(),
                SelectionPolicy(),
            ]
        )

    def resolve(self, request: CapabilityResolutionRequest) -> CapabilityResolutionResult:
        requested_capability_id = request.capability_id
        capability_id = (
            self.aliases.resolve(request.capability_id)
            if self.aliases is not None
            else request.capability_id
        )

        if not self.capabilities.has_capability(capability_id):
            return CapabilityResolutionResult(
                ok=False,
                capability_id=capability_id,
                explanation=(
                    f"Capability {requested_capability_id} resolved to "
                    f"{capability_id} but is not registered."
                ),
                metadata={
                    "requested_capability_id": requested_capability_id,
                    "diagnostics": _diagnostics(
                        status="capability_not_registered",
                        requested_capability_id=requested_capability_id,
                        resolved_capability_id=capability_id,
                    ),
                },
            )

        capability = self.capabilities.get_capability(capability_id)
        candidates = self.bindings.list_for_capability(capability_id)

        ctx = ResolutionContext(
            request=request,
            candidates=list(candidates),
        )
        self._build_pipeline().run(ctx)

        rejected: list[RejectedProvider] = ctx.rejected
        enabled = []

        for binding in ctx.candidates:

            enabled.append(binding)

        if not enabled:
            return CapabilityResolutionResult(
                ok=False,
                capability_id=capability_id,
                required_inputs=capability.required_inputs,
                explanation=f"No enabled provider binding found for {capability_id}.",
                rejected_providers=tuple(rejected),
                metadata={
                    "requested_capability_id": requested_capability_id,
                    "diagnostics": _diagnostics(
                        status="no_enabled_binding",
                        requested_capability_id=requested_capability_id,
                        resolved_capability_id=capability_id,
                        rejected_providers=tuple(rejected),
                    ),
                },
            )

        selected = ctx.selected

        if selected is None:
            raise RuntimeError(
                "Resolver pipeline produced candidates but selected no provider."
            )

        missing_inputs = tuple(
            key
            for key in selected.required_inputs
            if request.inputs.get(key) in (None, "")
        )

        if missing_inputs:
            return CapabilityResolutionResult(
                ok=False,
                capability_id=capability_id,
                selected_provider_id=selected.provider_id,
                provider_ref=selected.provider_ref,
                runtime_node_type=selected.runtime_node_type,
                required_inputs=selected.required_inputs,
                missing_inputs=missing_inputs,
                requires_approval=selected.requires_approval,
                risk=selected.risk,
                explanation=(
                    f"Selected provider {selected.provider_id}, "
                    f"but missing required inputs: {', '.join(missing_inputs)}."
                ),
                rejected_providers=tuple(rejected),
                metadata={
                    "requested_capability_id": requested_capability_id,
                    "diagnostics": _diagnostics(
                        status="missing_inputs",
                        requested_capability_id=requested_capability_id,
                        resolved_capability_id=capability_id,
                        selected_provider_id=selected.provider_id,
                        provider_ref=selected.provider_ref,
                        runtime_node_type=selected.runtime_node_type,
                        missing_inputs=missing_inputs,
                        rejected_providers=tuple(rejected),
                    ),
                },
            )

        return CapabilityResolutionResult(
            ok=True,
            capability_id=capability_id,
            selected_provider_id=selected.provider_id,
            provider_ref=selected.provider_ref,
            runtime_node_type=selected.runtime_node_type,
            required_inputs=selected.required_inputs,
            requires_approval=selected.requires_approval,
            risk=selected.risk,
            explanation=f"Selected provider {selected.provider_id}.",
            rejected_providers=tuple(rejected),
            metadata={
                "requested_capability_id": requested_capability_id,
                "capability_title": capability.title,
                "binding_priority": selected.priority,
                "diagnostics": _diagnostics(
                    status="selected",
                    requested_capability_id=requested_capability_id,
                    resolved_capability_id=capability_id,
                    selected_provider_id=selected.provider_id,
                    provider_ref=selected.provider_ref,
                    runtime_node_type=selected.runtime_node_type,
                    rejected_providers=tuple(rejected),
                    metadata={
                        "capability_title": capability.title,
                        "binding_priority": selected.priority,
                    },
                ),
            },
        )

__all__ = [
    "CapabilityResolver",
    "ResolverPipeline",
    "ResolutionContext",
    "ResolverPolicy",
    "BindingEnabledPolicy",
    "TenantAvailabilityPolicy",
    "ProviderHealthPolicy",
    "ProviderAuthPolicy",
    "CostPolicy",
    "LatencyPolicy",
    "RiskPolicy",
    "ApprovalPolicy",
    "AllowDenyPolicy",
    "RegionPolicy",
    "CapabilityConstraintPolicy",
    "SelectionPolicy",
]
