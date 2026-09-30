from __future__ import annotations

from typing import Any

from app.agents_runtime.tools import (
    AgentTool,
    ToolRegistry,
    ToolRiskLevel,
    build_builtin_tool_registry,
)


def build_test_tool_registry(
    *,
    tools: Any | None = None,
    user_id: Any | None = None,
) -> ToolRegistry:
    """
    Production registry plus deterministic tools owned only by tests.

    `tools.dangerous_test_action`, when supplied, lets workflow tests
    inject an execution probe while preserving the real approval path.
    """

    registry = build_builtin_tool_registry(
        tools=tools,
        user_id=user_id,
    )

    async def echo(
        text: str,
    ) -> dict[str, Any]:
        return {
            "text": text,
        }

    registry.register(
        AgentTool(
            name="echo",
            description=(
                "Test-only deterministic echo tool."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                    },
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            function=echo,
            risk_level=ToolRiskLevel.SAFE,
        )
    )

    async def dangerous_test_action(
        resource_id: str,
        amount: float,
    ) -> dict[str, Any]:
        injected = (
            getattr(
                tools,
                "dangerous_test_action",
                None,
            )
            if tools is not None
            else None
        )

        if injected is not None:
            result = injected(
                resource_id=resource_id,
                amount=amount,
            )

            if hasattr(result, "__await__"):
                result = await result

            return result

        return {
            "resource_id": resource_id,
            "amount": amount,
            "status": "test_action_created",
        }

    registry.register(
        AgentTool(
            name="dangerous_test_action",
            description=(
                "Test-only dangerous action used to verify "
                "approval, pause, resume and idempotency."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "resource_id": {
                        "type": "string",
                    },
                    "amount": {
                        "type": "number",
                    },
                },
                "required": [
                    "resource_id",
                    "amount",
                ],
                "additionalProperties": False,
            },
            function=dangerous_test_action,
            risk_level=ToolRiskLevel.DANGEROUS,
            requires_approval=True,
        )
    )

    return registry
