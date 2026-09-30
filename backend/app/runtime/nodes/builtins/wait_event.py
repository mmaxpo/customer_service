from __future__ import annotations

from typing import Any, Dict

from app.runtime.nodes.configs import WaitEventConfig
from app.runtime.nodes.base import BaseNode
from app.runtime.waits.types import RuntimeWait


class WaitEventNode(BaseNode):
    async def run(self, ctx, state: dict, config: WaitEventConfig) -> Dict[str, Any]:
        vars_ = state.get("vars") or {}
        resume_input = vars_.get("resume_input")

        if isinstance(resume_input, dict) and resume_input.get("wait_id"):
            return {
                "output": {
                    "resumed": True,
                    "wait_id": resume_input.get("wait_id"),
                    "event": resume_input.get("event") or {},
                    "resolution": resume_input.get("resolution") or {},
                },
                "patch": {},
                "meta": {
                    "resumed": True,
                    "wait_id": resume_input.get("wait_id"),
                    "event_type": config.event_type,
                },
            }

        return {
            "status": "paused",
            "wait": RuntimeWait(
                wait_type="event",
                payload={
                    "event_type": config.event_type,
                    "match": config.match or {},
                    "reason": config.reason,
                    "node_type": "wait.event",
                },
            ),
            "interrupt": {
                "kind": "event",
                "event_type": config.event_type,
                "match": config.match or {},
                "reason": config.reason,
                "node_type": "wait.event",
            },
            "output": None,
            "patch": {},
            "meta": {
                "paused": True,
                "wait_type": "event",
                "event_type": config.event_type,
            },
        }


NODE_TYPE = "wait.event"
NODE_CLS = WaitEventNode
CONFIG_MODEL = WaitEventConfig
