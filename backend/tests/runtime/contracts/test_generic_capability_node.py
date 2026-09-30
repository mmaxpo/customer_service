from types import SimpleNamespace

import pytest

from app.runtime.engine.executor import execute_workflow_dag
from app.runtime.resources import RuntimeServiceFactory


class FakeCapabilities:
    async def resolve(self, invocation):
        from app.runtime.capabilities.models import (
            CapabilityInvocationStatus,
            CapabilityResult,
        )

        assert invocation.capability_id == "shopify.get_order"
        assert invocation.inputs["order_ref"] == "#1001"

        return CapabilityResult(
            capability_id=invocation.capability_id,
            status=CapabilityInvocationStatus.OK,
            ok=True,
            output={"order_name": "#1001"},
            error_code=None,
            error_message=None,
            duration_ms=1.0,
            metadata={"fake": True},
        )


@pytest.mark.asyncio
async def test_generic_capability_node_invokes_service_capability():
    services = RuntimeServiceFactory.build(user_id="user_1")
    services.capabilities = FakeCapabilities()

    ctx = SimpleNamespace(
        user_id="user_1",
        services=services,
        db=None,
        tools=None,
        extras={},
        run_store=None,
        event_sink=None,
        workflow_run_id=None,
    )

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "type": "custom",
                "data": {"nodeType": "trigger.message"},
            },
            {
                "id": "invoke_order",
                "type": "custom",
                "data": {
                    "nodeType": "capability.invoke",
                    "config": {
                        "capability_id": "shopify.get_order",
                        "payload": {"order_ref": "#1001"},
                        "save_as": "shopify_order",
                    },
                },
            },
            {
                "id": "response",
                "type": "custom",
                "data": {
                    "nodeType": "response",
                    "config": {
                        "response_from": "vars",
                        "response_key": "shopify_order",
                        "raw": True,
                    },
                },
            },
        ],
        "edges": [
            {"source": "trigger", "target": "invoke_order"},
            {"source": "invoke_order", "target": "response"},
        ],
    }

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="Where is #1001?",
        strict=True,
    )

    assert result["meta"]["status"] == "ok", result
    assert result["answer"] == {"order_name": "#1001"}
    assert result["meta"]["outputs_by_node_id"]["invoke_order"] == {
        "order_name": "#1001"
    }
    assert (
        result["meta"]["node_meta_by_id"]["invoke_order"]["capability_id"]
        == "shopify.get_order"
    )


@pytest.mark.asyncio
async def test_generic_capability_node_can_return_structured_error_without_failing():
    services = RuntimeServiceFactory.build(user_id="user_1")

    ctx = SimpleNamespace(
        user_id="user_1",
        services=services,
        db=None,
        tools=None,
        extras={},
        run_store=None,
        event_sink=None,
        workflow_run_id=None,
    )

    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "type": "custom",
                "data": {"nodeType": "trigger.message"},
            },
            {
                "id": "invoke_missing",
                "type": "custom",
                "data": {
                    "nodeType": "capability.invoke",
                    "config": {
                        "capability_id": "shopify.get_order",
                        "payload": {},
                        "save_as": "capability_error",
                        "fail_on_error": False,
                    },
                },
            },
            {
                "id": "response",
                "type": "custom",
                "data": {
                    "nodeType": "response",
                    "config": {
                        "response_from": "vars",
                        "response_key": "capability_error",
                        "raw": True,
                    },
                },
            },
        ],
        "edges": [
            {"source": "trigger", "target": "invoke_missing"},
            {"source": "invoke_missing", "target": "response"},
        ],
    }

    result = await execute_workflow_dag(
        ctx=ctx,
        workflow=workflow,
        message="Where is my order?",
        strict=True,
    )

    assert result["meta"]["status"] == "ok", result
    assert result["answer"]["ok"] is False
    assert result["answer"]["error_code"] == "missing_order_ref"
