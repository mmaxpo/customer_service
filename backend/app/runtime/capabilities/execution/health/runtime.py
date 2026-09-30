from __future__ import annotations

from typing import Any

from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    CapabilityResolutionResult,
    CapabilityRisk,
    CapabilitySystem,
    RejectedProvider,
)
from app.runtime.capabilities.execution.health.enforcement import (
    ProviderHealthEnforcementMode,
    normalize_provider_health_enforcement_mode,
)
from app.runtime.capabilities.execution.health.probes import (
    ProviderHealthProbeCoordinator,
)
from app.runtime.capabilities.execution.health.reader import (
    ProviderHealthReader,
)
from app.runtime.capabilities.execution.policy.models import (
    CapabilityRuntimePolicy,
    CapabilityRuntimePolicySnapshot,
)


class ProviderHealthEnforcer:
    """Apply scoped provider-health policy before runtime execution."""

    def __init__(
        self,
        *,
        services: Any,
        system: CapabilitySystem,
        reader: ProviderHealthReader,
        probe_coordinator: ProviderHealthProbeCoordinator,
        mode: ProviderHealthEnforcementMode,
        probe_lease_seconds: int,
        probe_failure_cooldown_seconds: int,
    ) -> None:
        self.services = services
        self.system = system
        self.provider_health_reader = reader
        self.provider_health_probe_coordinator = probe_coordinator
        self.provider_health_mode = mode
        self.provider_health_probe_lease_seconds = (
            probe_lease_seconds
        )
        self.provider_health_probe_failure_cooldown_seconds = (
            probe_failure_cooldown_seconds
        )

    async def _apply_provider_health_mode(
        self,
        *,
        invocation: CapabilityInvocation,
        resolution: CapabilityResolutionResult,
        policy_snapshot: CapabilityRuntimePolicySnapshot | None = None,
    ) -> tuple[CapabilityResolutionResult, bool]:
        provider_id = resolution.selected_provider_id
        provider_ref = resolution.provider_ref

        # Constructor/factory configuration is the runtime baseline.
        # Durable policy only overrides it when an actual matching revision
        # was found. A Null reader or failed-open read must never replace an
        # explicit OFF or ENFORCE_UNHEALTHY mode with policy model defaults.
        if (
            policy_snapshot is not None
            and policy_snapshot.found
        ):
            policy = policy_snapshot.effective_policy
        else:
            policy = CapabilityRuntimePolicy(
                health_enforcement_mode=(
                    self.provider_health_mode.value
                ),
                health_probe_lease_seconds=(
                    self.provider_health_probe_lease_seconds
                ),
                health_probe_failure_cooldown_seconds=(
                    self.provider_health_probe_failure_cooldown_seconds
                ),
            )
        mode = normalize_provider_health_enforcement_mode(
            policy.health_enforcement_mode
        )

        if not resolution.ok or not provider_id or not provider_ref:
            return resolution, False

        if mode == ProviderHealthEnforcementMode.OFF:
            diagnostic = {
                "mode": mode.value,
                "read_attempted": False,
                "read_succeeded": None,
                "selection_enforced": False,
                "selected_provider_unchanged": True,
                "capability_id": resolution.capability_id,
                "provider_id": provider_id,
                "provider_ref": provider_ref,
            }
            return (
                self._attach_health_metadata(
                    resolution=resolution,
                    diagnostic=diagnostic,
                ),
                False,
            )

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

        try:
            snapshot = await self.provider_health_reader.get_effective_health(
                user_id=(
                    str(resolved_user_id) if resolved_user_id is not None else None
                ),
                tenant_id=(str(tenant_id) if tenant_id is not None else None),
                capability_id=resolution.capability_id,
                provider_id=provider_id,
                provider_ref=provider_ref,
            )

            restricted_state_enforced = bool(
                mode == ProviderHealthEnforcementMode.ENFORCE_UNHEALTHY
                and snapshot.found
                and snapshot.effective_state
                in {
                    "unhealthy",
                    "recovering",
                }
            )

            probe_diagnostic = None
            probe_allowed = False

            if restricted_state_enforced:
                probe_diagnostic = await self._try_health_probe(
                    invocation=invocation,
                    resolution=resolution,
                    snapshot=snapshot,
                    lease_seconds=(
                        policy.health_probe_lease_seconds
                    ),
                )
                probe_allowed = bool(probe_diagnostic.get("acquired"))

            should_reject = bool(restricted_state_enforced and not probe_allowed)

            diagnostic = {
                "mode": mode.value,
                "read_attempted": True,
                "read_succeeded": True,
                **snapshot.model_dump(mode="json"),
                "selection_enforced": should_reject,
                "selected_provider_unchanged": (not should_reject),
                "health_probe": probe_diagnostic,
                "enforcement_reason": (
                    (f"effective_state_{snapshot.effective_state}")
                    if should_reject
                    else (
                        (
                            "controlled_recovery_request"
                            if snapshot.effective_state == "recovering"
                            else "controlled_health_probe"
                        )
                        if probe_allowed
                        else None
                    )
                ),
            }
        except Exception as exc:
            # Scoped-health reads are fail-open in every mode.
            should_reject = False
            diagnostic = {
                "mode": mode.value,
                "read_attempted": True,
                "read_succeeded": False,
                "selection_enforced": False,
                "selected_provider_unchanged": True,
                "fail_open": True,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "capability_id": resolution.capability_id,
                "provider_id": provider_id,
                "provider_ref": provider_ref,
            }

        return (
            self._attach_health_metadata(
                resolution=resolution,
                diagnostic=diagnostic,
            ),
            should_reject,
        )

    async def _try_health_probe(
        self,
        *,
        invocation: CapabilityInvocation,
        resolution: CapabilityResolutionResult,
        snapshot,
        lease_seconds: int | None = None,
    ) -> dict[str, Any]:
        """
        Attempt one controlled request for a restricted provider.

        For unhealthy state this is the initial half-open probe. For
        recovering state it is a bounded recovery request. Manual overrides
        always win. Only SAFE capabilities without approval requirements are
        eligible.
        """

        if snapshot.override_active:
            return {
                "acquired": False,
                "reason": "manual_override_active",
            }

        if resolution.risk != CapabilityRisk.SAFE:
            return {
                "acquired": False,
                "reason": "resolution_not_safe",
            }

        if resolution.requires_approval:
            return {
                "acquired": False,
                "reason": "approval_required",
            }

        capability = self.system.capabilities.get_capability(resolution.capability_id)

        if capability.risk != CapabilityRisk.SAFE:
            return {
                "acquired": False,
                "reason": "capability_not_safe",
            }

        provider_id = resolution.selected_provider_id
        provider_ref = resolution.provider_ref

        if not provider_id or not provider_ref:
            return {
                "acquired": False,
                "reason": "provider_scope_incomplete",
            }

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

        claim = await self.provider_health_probe_coordinator.try_claim_probe(
            user_id=(str(resolved_user_id) if resolved_user_id is not None else None),
            tenant_id=(str(tenant_id) if tenant_id is not None else None),
            capability_id=resolution.capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            lease_seconds=(
                lease_seconds
                or self.provider_health_probe_lease_seconds
            ),
        )

        return claim.model_dump(mode="json")

    def _attach_health_metadata(
        self,
        *,
        resolution: CapabilityResolutionResult,
        diagnostic: dict[str, Any],
    ) -> CapabilityResolutionResult:
        metadata = dict(resolution.metadata or {})
        metadata["provider_health"] = diagnostic

        # Preserve Step 1M's public diagnostic key only when the effective
        # invocation policy is actually shadow mode.
        if (
            diagnostic.get("mode")
            == ProviderHealthEnforcementMode.SHADOW.value
        ):
            metadata["provider_health_shadow"] = diagnostic
        else:
            metadata.pop("provider_health_shadow", None)

        return resolution.model_copy(update={"metadata": metadata})

    @staticmethod
    def _merge_health_rejections(
        *,
        resolution: CapabilityResolutionResult,
        health_rejections: list[RejectedProvider],
    ) -> CapabilityResolutionResult:
        if not health_rejections:
            return resolution

        health_rejected_provider_ids = {item.provider_id for item in health_rejections}

        remaining_rejections = tuple(
            item
            for item in resolution.rejected_providers
            if not (
                item.provider_id in health_rejected_provider_ids
                and item.reason == "provider_denied"
            )
        )

        combined_rejections = tuple(health_rejections) + remaining_rejections

        metadata = dict(resolution.metadata or {})
        diagnostics = dict(metadata.get("diagnostics") or {})
        diagnostics["rejected_providers"] = [
            item.model_dump(mode="json") for item in combined_rejections
        ]

        metadata["diagnostics"] = diagnostics
        metadata["provider_health_enforcement"] = {
            "rejected_count": len(health_rejections),
            "rejected_providers": [
                item.model_dump(mode="json") for item in health_rejections
            ],
        }

        return resolution.model_copy(
            update={
                "rejected_providers": (combined_rejections),
                "metadata": metadata,
            }
        )
