from __future__ import annotations

from typing import Any

from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    CapabilityResolutionResult,
    CapabilitySystem,
    RejectedProvider,
)
from app.runtime.capabilities.execution.installation.models import (
    ProviderInstallationReader,
    ProviderInstallationSnapshot,
)


class ProviderInstallationEnforcer:
    """Apply durable provider-installation availability at runtime."""

    def __init__(
        self,
        *,
        services: Any,
        system: CapabilitySystem,
        reader: ProviderInstallationReader,
    ) -> None:
        self.services = services
        self.system = system
        self.provider_installation_reader = reader

    async def _evaluate_provider_installations(
        self,
        *,
        invocation: CapabilityInvocation,
        denied_provider_ids: tuple[str, ...],
    ) -> tuple[
        list[RejectedProvider],
        list[dict[str, Any]],
    ]:
        """
        Evaluate durable provider availability before scoring.

        The reader owns no credentials. It only reports whether an
        authenticated user's provider installation is enabled, configured,
        authenticated, and verified.

        Null readers remain fail-open for compatibility. Database readers
        fail closed when an installation is missing or unusable.
        """

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
            return [], []

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
        tenant_id = getattr(
            getattr(
                self.services,
                "identity",
                None,
            ),
            "tenant_id",
            None,
        )

        denied = set(denied_provider_ids)
        rejected: list[RejectedProvider] = []
        diagnostics: list[dict[str, Any]] = []
        evaluated_provider_ids: set[str] = set()

        for binding in (
            self.system.bindings
            .list_for_capability(capability_id)
        ):
            provider_id = binding.provider_id

            if (
                provider_id in denied
                or provider_id
                in evaluated_provider_ids
            ):
                continue

            evaluated_provider_ids.add(
                provider_id
            )

            provider = self.system.providers.get(
                provider_id
            )

            try:
                snapshot = await (
                    self.provider_installation_reader
                    .get_provider_installation(
                        user_id=resolved_user_id,
                        tenant_id=(
                            str(tenant_id)
                            if tenant_id is not None
                            else None
                        ),
                        provider_id=provider_id,
                    )
                )
            except Exception as exc:
                # Availability infrastructure failures remain fail-open. The
                # diagnostic records the failure without changing selection.
                diagnostics.append(
                    {
                        "provider_id": provider_id,
                        "provider_ref": (
                            binding.provider_ref
                        ),
                        "found": False,
                        "available": True,
                        "rejection_reason": None,
                        "read_succeeded": False,
                        "reader_error": str(exc),
                    }
                )
                continue

            reason = snapshot.rejection_reason(
                requires_auth=provider.requires_auth
            )

            item = self._provider_installation_diagnostic(
                snapshot=snapshot,
                provider_ref=binding.provider_ref,
                rejection_reason=reason,
                read_succeeded=True,
            )
            diagnostics.append(item)

            if reason is None:
                continue

            rejected.append(
                RejectedProvider(
                    provider_id=provider_id,
                    reason=reason,
                    metadata={
                        **item,
                        "requires_auth": (
                            provider.requires_auth
                        ),
                    },
                )
            )

        return rejected, diagnostics

    @staticmethod
    def _provider_installation_diagnostic(
        *,
        snapshot: ProviderInstallationSnapshot,
        provider_ref: str,
        rejection_reason: str | None,
        read_succeeded: bool,
    ) -> dict[str, Any]:
        return {
            "provider_id": snapshot.provider_id,
            "provider_ref": provider_ref,
            "found": snapshot.found,
            "available": snapshot.available,
            "enabled": snapshot.enabled,
            "configuration_state": (
                snapshot.configuration_state.value
            ),
            "authentication_state": (
                snapshot.authentication_state.value
            ),
            "verification_state": (
                snapshot.verification_state.value
            ),
            "integration_kind": (
                snapshot.integration_kind
            ),
            "integration_connection_id": (
                snapshot.integration_connection_id
            ),
            "failure_code": snapshot.failure_code,
            "failure_message": (
                snapshot.failure_message
            ),
            "version": snapshot.version,
            "rejection_reason": rejection_reason,
            "read_succeeded": read_succeeded,
            "metadata": dict(
                snapshot.metadata or {}
            ),
        }

    @staticmethod
    def _merge_installation_rejections(
        *,
        resolution: CapabilityResolutionResult,
        installation_rejections: list[
            RejectedProvider
        ],
        diagnostics: list[dict[str, Any]],
    ) -> CapabilityResolutionResult:
        existing = list(
            resolution.rejected_providers
        )
        existing_keys = {
            (
                item.provider_id,
                item.reason,
            )
            for item in existing
        }

        for item in installation_rejections:
            key = (
                item.provider_id,
                item.reason,
            )

            if key not in existing_keys:
                existing.append(item)
                existing_keys.add(key)

        metadata = dict(
            resolution.metadata or {}
        )
        metadata[
            "provider_installation_enforcement"
        ] = {
            "evaluated": bool(diagnostics),
            "candidates": diagnostics,
            "rejected_providers": [
                item.model_dump(mode="json")
                for item in installation_rejections
            ],
        }

        diagnostics_payload = dict(
            metadata.get("diagnostics") or {}
        )
        diagnostics_payload[
            "rejected_providers"
        ] = [
            item.model_dump(mode="json")
            for item in existing
        ]
        metadata["diagnostics"] = (
            diagnostics_payload
        )

        return resolution.model_copy(
            update={
                "rejected_providers": tuple(
                    existing
                ),
                "metadata": metadata,
            }
        )
