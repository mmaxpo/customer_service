from __future__ import annotations

from app.agents_runtime.tools.schemas import AgentTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool:
        tool = self._tools.get(name)

        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        return tool

    def list(self) -> list[AgentTool]:
        return list(self._tools.values())

    def selected(self, names: list[str]) -> list[AgentTool]:
        return [self.get(name) for name in names]

    def to_openai_tools(self, names: list[str] | None = None) -> list[dict]:
        tools = self.selected(names) if names else self.list()

        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools
        ]
