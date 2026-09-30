import pytest

from tests.agents_runtime.support import (
    build_test_tool_registry,
)

from app.agents_runtime.tools import (
    AgentTool,
    ToolExecutor,
    ToolRegistry,
    build_builtin_tool_registry,
)


def test_register_and_get_tool():
    registry = ToolRegistry()

    def hello(name: str):
        return {"message": f"Hello {name}"}

    registry.register(
        AgentTool(
            name="hello",
            description="Say hello.",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
            function=hello,
        )
    )

    tool = registry.get("hello")

    assert tool.name == "hello"


def test_duplicate_tool_fails():
    registry = build_builtin_tool_registry()
    tool = registry.get("calculator")

    with pytest.raises(ValueError):
        registry.register(tool)


@pytest.mark.asyncio
async def test_execute_calculator_tool():
    registry = build_builtin_tool_registry()
    executor = ToolExecutor(registry)

    result = await executor.execute(
        "calculator",
        {"expression": "25 * 19 + 7"},
    )

    assert result == {"result": 482}


def test_to_openai_tools_shape():
    registry = build_builtin_tool_registry()

    tools = registry.to_openai_tools(["calculator"])

    assert tools[0]["type"] == "function"
    assert tools[0]["name"] == "calculator"
    assert "parameters" in tools[0]


def test_dangerous_tool_requires_approval():
    registry = build_test_tool_registry()

    tool = registry.get("dangerous_test_action")

    assert tool.requires_approval is True
    assert tool.risk_level == "dangerous"
