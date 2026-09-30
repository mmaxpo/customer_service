from types import SimpleNamespace

import pytest

from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.execution import (
    CapabilityExecutionContext,
    CapabilityExecutorRegistry,
)
from app.runtime.capabilities.registry import (
    CapabilityResolutionResult,
)


def build_context() -> CapabilityExecutionContext:
    return CapabilityExecutionContext(
        invocation=CapabilityInvocation(
            capability_id="example.capability",
            inputs={"value": 42},
        ),
        resolution=CapabilityResolutionResult(
            ok=True,
            capability_id="example.capability",
            selected_provider_id="example",
            provider_ref="example.execute",
        ),
        services=SimpleNamespace(),
    )


@pytest.mark.asyncio
async def test_executor_registry_registers_and_executes_provider_ref():
    registry = CapabilityExecutorRegistry()
    calls = []

    async def executor(context):
        calls.append(context)
        return {
            "value": context.invocation.inputs["value"],
        }

    registry.register("example.execute", executor)

    result = await registry.execute(
        "example.execute",
        build_context(),
    )

    assert result == {"value": 42}
    assert len(calls) == 1
    assert registry.has("example.execute") is True
    assert registry.provider_refs() == ("example.execute",)


def test_executor_registry_rejects_duplicate_provider_ref():
    registry = CapabilityExecutorRegistry()

    async def executor(context):
        return None

    registry.register("example.execute", executor)

    with pytest.raises(
        ValueError,
        match="Capability executor already registered",
    ):
        registry.register("example.execute", executor)


def test_executor_registry_rejects_blank_provider_ref():
    registry = CapabilityExecutorRegistry()

    async def executor(context):
        return None

    with pytest.raises(ValueError, match="provider_ref is required"):
        registry.register("   ", executor)


def test_executor_registry_reports_unknown_provider_ref():
    registry = CapabilityExecutorRegistry()

    with pytest.raises(
        ValueError,
        match="No runtime provider executor registered for mock.get_order",
    ):
        registry.get("mock.get_order")
