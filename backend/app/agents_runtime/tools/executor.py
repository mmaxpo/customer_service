from __future__ import annotations

import inspect
from typing import Any

from app.agents_runtime.tools.registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        tool = self.registry.get(name)

        result = tool.function(**arguments)

        if inspect.isawaitable(result):
            result = await result

        return result
