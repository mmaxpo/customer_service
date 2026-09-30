from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.runtime.nodes.configs import WaitTimeConfig
from app.runtime.nodes.base import BaseNode
from app.runtime.waits.types import RuntimeWait


class WaitTimeNode(BaseNode):
    async def run(self, ctx, state: dict, config: WaitTimeConfig) -> Dict[str, Any]:
        vars_ = state.get("vars") or {}
        resume_input = vars_.get("resume_input")

        if isinstance(resume_input, dict):
            wait_id = resume_input.get("wait_id")
            if wait_id:
                return {
                    "output": {
                        "resumed": True,
                        "wait_id": wait_id,
                        "expired": bool(resume_input.get("expired", False)),
                        "resolution": resume_input.get("resolution") or {},
                    },
                    "patch": {},
                    "meta": {
                        "resumed": True,
                        "wait_id": wait_id,
                    },
                }

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=config.seconds)

        return {
            "status": "paused",
            "wait": RuntimeWait(
                wait_type="time",
                payload={
                    "seconds": config.seconds,
                    "reason": config.reason,
                    "node_type": "wait.time",
                },
                expires_at=expires_at,
            ),
            "interrupt": {
                "kind": "time",
                "seconds": config.seconds,
                "reason": config.reason,
                "node_type": "wait.time",
            },
            "output": None,
            "patch": {},
            "meta": {
                "paused": True,
                "wait_type": "time",
                "expires_at": expires_at.isoformat(),
            },
        }


NODE_TYPE = "wait.time"
NODE_CLS = WaitTimeNode
CONFIG_MODEL = WaitTimeConfig
