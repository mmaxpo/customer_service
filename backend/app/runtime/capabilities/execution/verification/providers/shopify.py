from __future__ import annotations

from typing import Any

from app.runtime.capabilities.execution.verification.contracts import (
    TaskVerificationContext,
    TaskVerificationEvidence,
    TaskVerificationMethod,
    TaskVerificationOutcome,
    TaskVerificationResult,
)
from app.runtime.capabilities.execution.verification.registry import (
    TaskVerifierRegistry,
)


class ShopifyRefundPreparationVerifier:
    """
    Verify only refund preparation.

    The current real Shopify provider does not submit money-moving refunds.
    Therefore this verifier must never claim that the customer was refunded.
    """

    async def verify(
        self,
        context: TaskVerificationContext,
    ) -> TaskVerificationResult:
        request = context.request
        output = (
            request.execution_output
            if isinstance(
                request.execution_output,
                dict,
            )
            else {}
        )
        payload = output.get("payload")

        if not isinstance(payload, dict):
            payload = output

        status = str(
            payload.get("status")
            or output.get("status")
            or ""
        ).strip().lower()

        evidence = TaskVerificationEvidence(
            kind="refund_preparation",
            source="capability_execution",
            data={
                "status": status or None,
                "order_id": (
                    payload.get("order_id")
                    or output.get("order_id")
                ),
                "order_name": (
                    payload.get("order_name")
                    or output.get("order_name")
                ),
                "requested_amount": (
                    request.inputs.get("amount")
                ),
                "prepared_amount": (
                    payload.get("amount")
                ),
            },
        )

        if status == "prepared":
            return _result(
                context=context,
                outcome=(
                    TaskVerificationOutcome
                    .PARTIALLY_VERIFIED
                ),
                method=(
                    TaskVerificationMethod
                    .EXECUTION_EVIDENCE
                ),
                reason_code=(
                    "refund_prepared_not_submitted"
                ),
                summary=(
                    "Refund preparation was confirmed, "
                    "but no Shopify refund was submitted."
                ),
                confidence=1.0,
                retryable=False,
                observed_outcome={
                    "refund_prepared": True,
                    "refund_submitted": False,
                    "refund_completed": False,
                },
                evidence=[evidence],
            )

        if status == "blocked":
            return _result(
                context=context,
                outcome=(
                    TaskVerificationOutcome.FAILED
                ),
                method=(
                    TaskVerificationMethod
                    .EXECUTION_EVIDENCE
                ),
                reason_code=(
                    "refund_preparation_blocked"
                ),
                summary=(
                    "The refund was not prepared "
                    "because the action was blocked."
                ),
                confidence=1.0,
                retryable=False,
                observed_outcome={
                    "refund_prepared": False,
                    "refund_submitted": False,
                    "refund_completed": False,
                },
                evidence=[evidence],
            )

        return _result(
            context=context,
            outcome=(
                TaskVerificationOutcome
                .INCONCLUSIVE
            ),
            method=(
                TaskVerificationMethod
                .EXECUTION_EVIDENCE
            ),
            reason_code=(
                "refund_preparation_status_unknown"
            ),
            summary=(
                "The execution response does not "
                "prove refund preparation."
            ),
            confidence=0.0,
            retryable=False,
            observed_outcome={
                "refund_prepared": None,
                "refund_submitted": None,
                "refund_completed": None,
            },
            evidence=[evidence],
        )


class ShopifyCancelOutcomeVerifier:
    """
    Verify cancellation by reading fresh Shopify order state.

    The original cancellation response is not treated as proof. A successful
    result requires the newly observed Shopify order to contain cancelled_at.
    """

    async def verify(
        self,
        context: TaskVerificationContext,
    ) -> TaskVerificationResult:
        request = context.request

        order_ref = str(
            request.inputs.get("order_ref")
            or ""
        ).strip()

        if not order_ref:
            return _result(
                context=context,
                outcome=(
                    TaskVerificationOutcome
                    .NOT_VERIFIABLE
                ),
                method=(
                    TaskVerificationMethod
                    .REMOTE_STATE
                ),
                reason_code=(
                    "cancel_order_ref_missing"
                ),
                summary=(
                    "Cancellation cannot be verified "
                    "without an order reference."
                ),
                confidence=1.0,
                retryable=False,
            )

        shopify = _require_shopify_service(
            context
        )

        try:
            order = await (
                shopify.get_order_fresh(
                    user_id=request.user_id,
                    order_ref=order_ref,
                )
            )
        except Exception as exc:
            return _result(
                context=context,
                outcome=(
                    TaskVerificationOutcome
                    .INCONCLUSIVE
                ),
                method=(
                    TaskVerificationMethod
                    .REMOTE_STATE
                ),
                reason_code=(
                    "cancel_remote_observation_failed"
                ),
                summary=(
                    "Fresh Shopify order state could "
                    "not be retrieved."
                ),
                confidence=0.0,
                retryable=True,
                evidence=[
                    TaskVerificationEvidence(
                        kind=(
                            "remote_observation_error"
                        ),
                        source="shopify",
                        data={
                            "order_ref": order_ref,
                            "exception_type": (
                                type(exc).__name__
                            ),
                        },
                    )
                ],
            )

        if not isinstance(order, dict):
            return _result(
                context=context,
                outcome=(
                    TaskVerificationOutcome
                    .INCONCLUSIVE
                ),
                method=(
                    TaskVerificationMethod
                    .REMOTE_STATE
                ),
                reason_code=(
                    "cancel_order_not_observed"
                ),
                summary=(
                    "Shopify did not return an order "
                    "for cancellation verification."
                ),
                confidence=0.0,
                retryable=True,
            )

        cancelled_at = order.get(
            "cancelled_at"
        )

        evidence = TaskVerificationEvidence(
            kind="shopify_order_state",
            source="shopify",
            data={
                "order_id": order.get("id"),
                "order_name": order.get("name"),
                "cancelled_at": cancelled_at,
                "financial_status": order.get(
                    "financial_status"
                ),
                "fulfillment_status": order.get(
                    "fulfillment_status"
                ),
            },
        )

        if cancelled_at:
            return _result(
                context=context,
                outcome=(
                    TaskVerificationOutcome
                    .VERIFIED
                ),
                method=(
                    TaskVerificationMethod
                    .REMOTE_STATE
                ),
                reason_code=(
                    "shopify_order_cancelled"
                ),
                summary=(
                    "Fresh Shopify state confirms "
                    "that the order is cancelled."
                ),
                confidence=1.0,
                retryable=False,
                observed_outcome={
                    "order_cancelled": True,
                    "cancelled_at": cancelled_at,
                },
                evidence=[evidence],
            )

        return _result(
            context=context,
            outcome=(
                TaskVerificationOutcome.FAILED
            ),
            method=(
                TaskVerificationMethod
                .REMOTE_STATE
            ),
            reason_code=(
                "shopify_order_not_cancelled"
            ),
            summary=(
                "Fresh Shopify state shows that "
                "the order is not cancelled."
            ),
            confidence=1.0,
            retryable=False,
            observed_outcome={
                "order_cancelled": False,
                "cancelled_at": None,
            },
            evidence=[evidence],
        )


class ShopifyAddressChangePreparationVerifier:
    """
    Verify only address-change preparation.

    The current real Shopify provider does not submit address mutations.
    Therefore this verifier must never claim the address was changed.
    """

    async def verify(
        self,
        context: TaskVerificationContext,
    ) -> TaskVerificationResult:
        request = context.request
        output = (
            request.execution_output
            if isinstance(request.execution_output, dict)
            else {}
        )
        payload = output.get("payload")

        if not isinstance(payload, dict):
            payload = output

        status = str(
            payload.get("status")
            or output.get("status")
            or ""
        ).strip().lower()

        evidence = TaskVerificationEvidence(
            kind="address_change_preparation",
            source="capability_execution",
            data={
                "status": status or None,
                "order_id": (
                    payload.get("order_id")
                    or output.get("order_id")
                ),
                "requested_address": request.inputs.get("new_address"),
            },
        )

        if status == "prepared":
            return _result(
                context=context,
                outcome=TaskVerificationOutcome.PARTIALLY_VERIFIED,
                method=TaskVerificationMethod.EXECUTION_EVIDENCE,
                reason_code="address_change_prepared_not_submitted",
                summary=(
                    "Address-change preparation was confirmed, "
                    "but no Shopify address update was submitted."
                ),
                confidence=1.0,
                retryable=False,
                observed_outcome={
                    "address_change_prepared": True,
                    "address_change_submitted": False,
                },
                evidence=[evidence],
            )

        if status == "blocked":
            return _result(
                context=context,
                outcome=TaskVerificationOutcome.FAILED,
                method=TaskVerificationMethod.EXECUTION_EVIDENCE,
                reason_code="address_change_preparation_blocked",
                summary=(
                    "The address change was not prepared "
                    "because the action was blocked."
                ),
                confidence=1.0,
                retryable=False,
                observed_outcome={
                    "address_change_prepared": False,
                    "address_change_submitted": False,
                },
                evidence=[evidence],
            )

        return _result(
            context=context,
            outcome=TaskVerificationOutcome.INCONCLUSIVE,
            method=TaskVerificationMethod.EXECUTION_EVIDENCE,
            reason_code="address_change_preparation_status_unknown",
            summary=(
                "The execution response does not "
                "prove address-change preparation."
            ),
            confidence=0.0,
            retryable=False,
            observed_outcome={
                "address_change_prepared": None,
                "address_change_submitted": None,
            },
            evidence=[evidence],
        )


class ShopifyReshipPreparationVerifier:
    """
    Verify only reship preparation.

    The current real Shopify provider does not submit replacement shipments.
    Therefore this verifier must never claim a reship was submitted.
    """

    async def verify(
        self,
        context: TaskVerificationContext,
    ) -> TaskVerificationResult:
        request = context.request
        output = (
            request.execution_output
            if isinstance(request.execution_output, dict)
            else {}
        )
        payload = output.get("payload")

        if not isinstance(payload, dict):
            payload = output

        status = str(
            payload.get("status")
            or output.get("status")
            or ""
        ).strip().lower()

        evidence = TaskVerificationEvidence(
            kind="reship_preparation",
            source="capability_execution",
            data={
                "status": status or None,
                "order_id": (
                    payload.get("order_id")
                    or output.get("order_id")
                ),
            },
        )

        if status == "prepared":
            return _result(
                context=context,
                outcome=TaskVerificationOutcome.PARTIALLY_VERIFIED,
                method=TaskVerificationMethod.EXECUTION_EVIDENCE,
                reason_code="reship_prepared_not_submitted",
                summary=(
                    "Reship preparation was confirmed, "
                    "but no replacement shipment was submitted."
                ),
                confidence=1.0,
                retryable=False,
                observed_outcome={
                    "reship_prepared": True,
                    "reship_submitted": False,
                },
                evidence=[evidence],
            )

        if status == "blocked":
            return _result(
                context=context,
                outcome=TaskVerificationOutcome.FAILED,
                method=TaskVerificationMethod.EXECUTION_EVIDENCE,
                reason_code="reship_preparation_blocked",
                summary=(
                    "The reship was not prepared "
                    "because the action was blocked."
                ),
                confidence=1.0,
                retryable=False,
                observed_outcome={
                    "reship_prepared": False,
                    "reship_submitted": False,
                },
                evidence=[evidence],
            )

        return _result(
            context=context,
            outcome=TaskVerificationOutcome.INCONCLUSIVE,
            method=TaskVerificationMethod.EXECUTION_EVIDENCE,
            reason_code="reship_preparation_status_unknown",
            summary=(
                "The execution response does not "
                "prove reship preparation."
            ),
            confidence=0.0,
            retryable=False,
            observed_outcome={
                "reship_prepared": None,
                "reship_submitted": None,
            },
            evidence=[evidence],
        )


def register_shopify_task_verifiers(
    registry: TaskVerifierRegistry,
) -> None:
    registry.register(
        "shopify.order_action:refund",
        ShopifyRefundPreparationVerifier(),
    )
    registry.register(
        "shopify.order_action:cancel",
        ShopifyCancelOutcomeVerifier(),
    )
    registry.register(
        "shopify.order_action:update_shipping_address",
        ShopifyAddressChangePreparationVerifier(),
    )
    registry.register(
        "shopify.order_action:reship",
        ShopifyReshipPreparationVerifier(),
    )


def _require_shopify_service(
    context: TaskVerificationContext,
) -> Any:
    services = context.services

    shopify = getattr(
        getattr(
            services,
            "business",
            None,
        ),
        "shopify",
        None,
    )

    if shopify is None:
        shopify = getattr(
            services,
            "shopify",
            None,
        )

    if shopify is None:
        raise ValueError(
            "Shopify task verification requires "
            "a Shopify business service"
        )

    return shopify


def _result(
    *,
    context: TaskVerificationContext,
    outcome: TaskVerificationOutcome,
    method: TaskVerificationMethod,
    reason_code: str,
    summary: str,
    confidence: float,
    retryable: bool,
    observed_outcome: (
        dict[str, Any] | None
    ) = None,
    evidence: (
        list[TaskVerificationEvidence]
        | None
    ) = None,
) -> TaskVerificationResult:
    request = context.request

    return TaskVerificationResult(
        verification_id=(
            request.verification_id
        ),
        capability_id=(
            request.capability_id
        ),
        provider_id=request.provider_id,
        provider_ref=request.provider_ref,
        action=(
            request.action
            or request.inputs.get("action")
        ),
        outcome=outcome,
        method=method,
        reason_code=reason_code,
        summary=summary,
        confidence=confidence,
        retryable=retryable,
        observed_outcome=(
            observed_outcome or {}
        ),
        evidence=evidence or [],
    )


__all__ = [
    "ShopifyCancelOutcomeVerifier",
    "ShopifyRefundPreparationVerifier",
    "register_shopify_task_verifiers",
]
