from uuid import uuid4

import pytest

from app.domains.customer_service.services.shopify import ShopifyService
from app.runtime_services import ShopifyRuntimeService


@pytest.mark.asyncio
async def test_application_shopify_runtime_service_forwards_action_scope(
    monkeypatch,
):
    user_id = uuid4()

    scope = {
        "line_items": [
            {
                "line_item_id": "101",
                "quantity": 1,
                "amount": None,
            }
        ],
        "replacement_line_item_id": None,
        "replacement_quantity": None,
        "new_address": None,
    }

    captured = {}

    async def fake_perform_order_action(
        self,
        *,
        user_id,
        action,
        order_ref,
        reason=None,
        note=None,
        new_address=None,
        amount=None,
        scope=None,
        idempotency_key=None,
        approval_wait_id=None,
        workflow_run_id=None,
    ):
        captured.update(
            {
                "user_id": user_id,
                "action": action,
                "order_ref": order_ref,
                "reason": reason,
                "note": note,
                "new_address": new_address,
                "amount": amount,
                "scope": scope,
                "idempotency_key": idempotency_key,
                "approval_wait_id": approval_wait_id,
                "workflow_run_id": workflow_run_id,
            }
        )

        return {
            "status": "prepared",
            "scope": scope,
        }

    monkeypatch.setattr(
        ShopifyService,
        "perform_order_action",
        fake_perform_order_action,
    )

    facade = ShopifyRuntimeService(db=object())

    result = await facade.perform_order_action(
        user_id=user_id,
        action="refund",
        order_ref="#1003",
        reason="Approved damaged-item partial refund",
        scope=scope,
        idempotency_key=(
            "support-review:test-plan:partial-refund"
        ),
    )

    assert result == {
        "status": "prepared",
        "scope": scope,
    }

    assert captured == {
        "user_id": user_id,
        "action": "refund",
        "order_ref": "#1003",
        "reason": "Approved damaged-item partial refund",
        "note": None,
        "new_address": None,
        "amount": None,
        "scope": scope,
        "idempotency_key": (
            "support-review:test-plan:partial-refund"
        ),
        "approval_wait_id": None,
        "workflow_run_id": None,
    }
