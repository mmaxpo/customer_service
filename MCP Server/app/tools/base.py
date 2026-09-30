from abc import ABC, abstractmethod


class MCPTool(ABC):
    name: str

    @abstractmethod
    async def run(self, payload: dict) -> dict:
        pass
