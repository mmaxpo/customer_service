from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.capabilities.models import (
    CapabilityInvocation,
    CapabilityResult,
)


class CapabilityExecutionOutcomeStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CapabilityExecutionAttempt(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider_id: str | None = None
    provider_ref: str | None = None
    capability_id: str | None = None
    outcome: str
    duration_ms: float | None = None

    error_code: str | None = None
    error_message: str | None = None
    failure_kind: str | None = None
    exception_type: str | None = None

    fallback_allowed: bool = False

    health_probe: bool = False
    health_probe_lease_token: str | None = None


class CapabilityExecutionOutcome(BaseModel):
    """
    Stable final outcome for one public capability invocation.

    CapabilityResult remains the caller-facing execution response. This model
    is the normalized observability, evaluation, repair, and learning contract.
    """

    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    requested_capability_id: str
    resolved_capability_id: str | None = None

    status: CapabilityExecutionOutcomeStatus
    ok: bool

    selected_provider_id: str | None = None
    provider_ref: str | None = None

    fallback_used: bool = False
    attempts: list[CapabilityExecutionAttempt] = Field(
        default_factory=list
    )

    error_code: str | None = None
    error_message: str | None = None
    failure_kind: str | None = None
    exception_type: str | None = None

    duration_ms: float | None = None
    user_id: str | None = None
    tenant_id: str | None = None

    invocation_metadata: dict[str, Any] = Field(
        default_factory=dict
    )
    result_metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    verification_context: dict[str, Any] | None = None

    created_at_ts: float = Field(default_factory=time.time)


def build_task_verification_context(
    *,
    invocation: CapabilityInvocation,
    result: CapabilityResult,
    provider_id: str | None,
    provider_ref: str | None,
) -> dict[str, Any] | None:
    """
    Build the minimum durable evidence required for automatic verification.

    Raw invocation inputs are intentionally not copied. Notes, addresses,
    credentials, and provider idempotency keys must not enter platform events.
    """

    if not result.ok:
        return None

    normalized_provider_ref = str(
        provider_ref or ""
    ).strip()
    normalized_provider_id = str(
        provider_id or ""
    ).strip()

    if (
        normalized_provider_id != "shopify"
        or normalized_provider_ref
        != "shopify.order_action"
    ):
        return None

    action = str(
        invocation.inputs.get("action") or ""
    ).strip().lower()

    if action not in {
        "cancel",
        "refund",
        "update_shipping_address",
        "reship",
    }:
        return None

    order_ref = str(
        invocation.inputs.get("order_ref") or ""
    ).strip()

    if not order_ref:
        return None

    inputs: dict[str, Any] = {
        "action": action,
        "order_ref": order_ref,
    }

    if (
        action == "refund"
        and invocation.inputs.get("amount")
        is not None
    ):
        inputs["amount"] = str(
            invocation.inputs["amount"]
        )

    if (
        action == "update_shipping_address"
        and invocation.inputs.get("new_address")
        is not None
    ):
        inputs["new_address"] = invocation.inputs["new_address"]

    if action == "cancel":
        expected_outcome = {
            "order_cancelled": True,
        }
    elif action == "refund":
        expected_outcome = {
            "refund_prepared": True,
            "refund_submitted": False,
            "refund_completed": False,
        }
    elif action == "update_shipping_address":
        expected_outcome = {
            "address_change_prepared": True,
            "address_change_submitted": False,
        }
    else:
        expected_outcome = {
            "reship_prepared": True,
            "reship_submitted": False,
        }

    return {
        "action": action,
        "inputs": inputs,
        "expected_outcome": expected_outcome,
        "execution_output": result.output,
    }


def build_capability_execution_outcome(
    *,
    invocation: CapabilityInvocation,
    result: CapabilityResult,
    tenant_id: Any = None,
) -> CapabilityExecutionOutcome:
    metadata = dict(result.metadata or {})

    raw_attempts = metadata.get("execution_attempts") or []
    attempts = [
        CapabilityExecutionAttempt.model_validate(item)
        for item in raw_attempts
        if isinstance(item, dict)
    ]

    return CapabilityExecutionOutcome(
        correlation_id=invocation.correlation_id,
        requested_capability_id=invocation.capability_id,
        resolved_capability_id=metadata.get(
            "resolved_capability_id"
        ),
        status=(
            CapabilityExecutionOutcomeStatus.SUCCEEDED
            if result.ok
            else CapabilityExecutionOutcomeStatus.FAILED
        ),
        ok=result.ok,
        selected_provider_id=metadata.get(
            "selected_provider_id"
        ),
        provider_ref=metadata.get("provider_ref"),
        fallback_used=bool(metadata.get("fallback_used")),
        attempts=attempts,
        error_code=result.error_code,
        error_message=result.error_message,
        failure_kind=metadata.get("failure_kind"),
        exception_type=metadata.get("exception_type"),
        duration_ms=result.duration_ms,
        user_id=(
            str(invocation.user_id)
            if invocation.user_id is not None
            else None
        ),
        tenant_id=(
            str(tenant_id)
            if tenant_id is not None
            else None
        ),
        invocation_metadata=dict(invocation.metadata or {}),
        result_metadata=metadata,
        verification_context=(
            build_task_verification_context(
                invocation=invocation,
                result=result,
                provider_id=metadata.get(
                    "selected_provider_id"
                ),
                provider_ref=metadata.get(
                    "provider_ref"
                ),
            )
        ),
    )


__all__ = [
    "CapabilityExecutionAttempt",
    "CapabilityExecutionOutcome",
    "CapabilityExecutionOutcomeStatus",
    "build_capability_execution_outcome",
    "build_task_verification_context",
]
