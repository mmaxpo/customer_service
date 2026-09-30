from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.runtime.capabilities.execution.verification import (
    TaskVerificationContext,
    TaskVerificationOutcome,
    TaskVerificationRequest,
    TaskVerifierRegistry,
    build_default_task_verifier_registry,
)


class FakeShopifyVerificationService:
    def __init__(
        self,
        order=None,
        error: Exception | None = None,
    ):
        self.order = order
        self.error = error
        self.calls = []

    async def get_order_fresh(
        self,
        *,
        user_id,
        order_ref,
    ):
        self.calls.append(
            {
                "user_id": user_id,
                "order_ref": order_ref,
            }
        )

        if self.error is not None:
            raise self.error

        return self.order


def services_with_shopify(shopify):
    return SimpleNamespace(
        business=SimpleNamespace(
            shopify=shopify
        )
    )


@pytest.mark.asyncio
async def test_refund_preparation_is_only_partially_verified():
    registry = (
        build_default_task_verifier_registry()
    )

    result = await registry.verify(
        TaskVerificationContext(
            request=TaskVerificationRequest(
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                provider_ref=(
                    "shopify.order_action"
                ),
                action="refund",
                user_id="user_1",
                inputs={
                    "action": "refund",
                    "order_ref": "#1001",
                    "amount": "25.00",
                },
                execution_output={
                    "action": "refund",
                    "order_id": "1001",
                    "status": "prepared",
                    "payload": {
                        "status": "prepared",
                        "amount": "25.00",
                        "order_id": "1001",
                    },
                },
            )
        )
    )

    assert (
        result.outcome
        == TaskVerificationOutcome
        .PARTIALLY_VERIFIED
    )
    assert (
        result.reason_code
        == "refund_prepared_not_submitted"
    )
    assert (
        result.observed_outcome[
            "refund_prepared"
        ]
        is True
    )
    assert (
        result.observed_outcome[
            "refund_completed"
        ]
        is False
    )


@pytest.mark.asyncio
async def test_cancel_is_verified_from_fresh_remote_state():
    shopify = FakeShopifyVerificationService(
        order={
            "id": "1002",
            "name": "#1002",
            "cancelled_at": (
                "2026-07-18T12:00:00Z"
            ),
            "financial_status": "voided",
            "fulfillment_status": None,
        }
    )
    registry = (
        build_default_task_verifier_registry()
    )

    result = await registry.verify(
        TaskVerificationContext(
            request=TaskVerificationRequest(
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                provider_ref=(
                    "shopify.order_action"
                ),
                action="cancel",
                user_id="user_2",
                inputs={
                    "action": "cancel",
                    "order_ref": "#1002",
                },
                execution_output={
                    "status": "cancelled",
                },
            ),
            services=services_with_shopify(
                shopify
            ),
        )
    )

    assert (
        result.outcome
        == TaskVerificationOutcome.VERIFIED
    )
    assert (
        result.reason_code
        == "shopify_order_cancelled"
    )
    assert result.confidence == 1.0
    assert shopify.calls == [
        {
            "user_id": "user_2",
            "order_ref": "#1002",
        }
    ]


@pytest.mark.asyncio
async def test_cancel_execution_success_does_not_override_remote_failure():
    shopify = FakeShopifyVerificationService(
        order={
            "id": "1003",
            "name": "#1003",
            "cancelled_at": None,
            "financial_status": "paid",
            "fulfillment_status": None,
        }
    )

    result = await (
        build_default_task_verifier_registry()
        .verify(
            TaskVerificationContext(
                request=TaskVerificationRequest(
                    capability_id=(
                        "ecommerce.orders.manage"
                    ),
                    provider_id="shopify",
                    provider_ref=(
                        "shopify.order_action"
                    ),
                    action="cancel",
                    user_id="user_3",
                    inputs={
                        "action": "cancel",
                        "order_ref": "#1003",
                    },
                    execution_output={
                        "status": "cancelled",
                    },
                ),
                services=(
                    services_with_shopify(
                        shopify
                    )
                ),
            )
        )
    )

    assert (
        result.outcome
        == TaskVerificationOutcome.FAILED
    )
    assert (
        result.reason_code
        == "shopify_order_not_cancelled"
    )
    assert (
        result.observed_outcome[
            "order_cancelled"
        ]
        is False
    )


@pytest.mark.asyncio
async def test_cancel_remote_read_failure_is_retryable_inconclusive():
    shopify = FakeShopifyVerificationService(
        error=RuntimeError(
            "temporary provider failure"
        )
    )

    result = await (
        build_default_task_verifier_registry()
        .verify(
            TaskVerificationContext(
                request=TaskVerificationRequest(
                    capability_id=(
                        "ecommerce.orders.manage"
                    ),
                    provider_id="shopify",
                    provider_ref=(
                        "shopify.order_action"
                    ),
                    action="cancel",
                    user_id="user_4",
                    inputs={
                        "action": "cancel",
                        "order_ref": "#1004",
                    },
                ),
                services=(
                    services_with_shopify(
                        shopify
                    )
                ),
            )
        )
    )

    assert (
        result.outcome
        == TaskVerificationOutcome
        .INCONCLUSIVE
    )
    assert result.retryable is True
    assert (
        result.reason_code
        == "cancel_remote_observation_failed"
    )
    assert (
        result.evidence[0]
        .data["exception_type"]
        == "RuntimeError"
    )
    assert (
        "temporary provider failure"
        not in str(
            result.model_dump(
                mode="json"
            )
        )
    )


def test_task_verifier_registry_rejects_duplicates():
    registry = TaskVerifierRegistry()
    verifier = (
        build_default_task_verifier_registry()
        .get(
            "shopify.order_action:cancel"
        )
    )

    registry.register(
        "shopify.order_action:cancel",
        verifier,
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            "shopify.order_action:cancel",
            verifier,
        )


@pytest.mark.asyncio
async def test_task_verifier_registry_rejects_unknown_action():
    registry = (
        build_default_task_verifier_registry()
    )

    with pytest.raises(
        ValueError,
        match="No task verifier registered",
    ):
        await registry.verify(
            TaskVerificationContext(
                request=TaskVerificationRequest(
                    capability_id=(
                        "ecommerce.orders.manage"
                    ),
                    provider_id="shopify",
                    provider_ref=(
                        "shopify.order_action"
                    ),
                    action="shipping_status",
                    user_id="user_5",
                    inputs={
                        "action": "reship",
                        "order_ref": "#1005",
                    },
                )
            )
        )
