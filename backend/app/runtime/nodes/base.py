from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseNode(ABC):
    """
    Canonical interface for all workflow nodes.

    Every executable node should implement:

        async def run(ctx, state, config) -> dict

    Args received by node.run:
        ctx:
            RuntimeContext or NodeCtx. Gives access to db, user_id, tools,
            run_store, event_sink, etc.

        state:
            Stable RunState snapshot. Nodes should read from this state but
            should not mutate it directly.

        config:
            Parsed Pydantic config for this node type.

    Required return shape:
        {
            "output": Any,
            "patch": dict,
            "meta": dict,
            "route": str | None,
            "status": str | None,
        }

    Common return examples:

        Normal output:
            {
                "output": "Hello",
                "patch": {},
                "meta": {},
            }

        Save shared variable:
            {
                "output": "refund",
                "patch": {"vars": {"intent": "refund"}},
                "meta": {},
            }

        Router:
            {
                "output": "Refund path selected",
                "route": "refund",
                "patch": {"vars": {"route_key": "refund"}},
                "meta": {},
            }

        Pause workflow:
            {
                "status": "paused",
                "output": "Waiting for approval",
                "interrupt": {"question": "Approve refund?"},
                "patch": {},
                "meta": {},
            }

    Important:
        Nodes should not write directly to shared state. They should return a
        patch and let the engine merge it deterministically.
    """

    @abstractmethod
    async def run(self, ctx, state: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """
        Execute the node.

        Implementations must return a dict result. The engine will validate and
        merge the result.

        Example:
            return {
                "output": "Done",
                "patch": {"vars": {"done": True}},
                "meta": {"source": "example"},
            }
        """
        raise NotImplementedError
