from __future__ import annotations

from fastapi import APIRouter

from app.agents_runtime.tools import build_builtin_tool_registry

router = APIRouter(prefix="/catalog", tags=["tool-catalog"])


@router.get("/tools")
async def list_agent_tools():
    registry = build_builtin_tool_registry()

    tools = []

    for tool in registry.list():
        if tool.name.startswith("fake_") or tool.name == "echo":
            continue

        tools.append(
            {
                "name": tool.name,
                "title": tool.name.replace("_", " ").title(),
                "description": tool.description,
                "parameters": tool.parameters,
                "risk_level": tool.risk_level,
                "requires_approval": tool.requires_approval,
                "provider": "builtin",
            }
        )

    return {"tools": tools}
