from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from app.runtime.nodes.base import BaseNode
from app.runtime.nodes.configs import HumanApprovalConfig
from app.runtime.waits.types import RuntimeWait


class HumanApprovalNode(BaseNode):
    async def run(
        self,
        ctx,
        state: dict,
        config: HumanApprovalConfig,
    ) -> Dict[str, Any]:
        vars_ = state.get("vars") or {}
        resume_input = vars_.get(config.input_key)

        if not isinstance(resume_input, dict):
            wait_payload: Dict[str, Any] = {
                "kind": "approval",
                "question": config.question,
                "expected": {
                    config.field: "boolean",
                },
                "node_type": "human.approval",
                "input_key": config.input_key,
                "field": config.field,
                "save_as": config.save_as,
            }

            interrupt: Dict[str, Any] = {
                "kind": "approval",
                "question": config.question,
                "expected": {
                    config.field: "boolean",
                },
                "node_type": "human.approval",
            }

            if config.context_key:
                context_value = deepcopy(
                    vars_.get(config.context_key)
                )

                wait_payload[
                    config.context_payload_key
                ] = context_value
                interrupt[
                    config.context_payload_key
                ] = context_value

                wait_payload["context_key"] = (
                    config.context_key
                )
                interrupt["context_key"] = (
                    config.context_key
                )

            return {
                "status": "paused",
                "wait": RuntimeWait(
                    wait_type="approval",
                    payload=wait_payload,
                ),
                "interrupt": interrupt,
                "output": None,
                "patch": {},
                "meta": {
                    "paused": True,
                    "wait_type": "approval",
                    "context_key": config.context_key,
                },
            }

        approved = bool(
            resume_input.get(
                config.field,
                False,
            )
        )

        patch_vars: Dict[str, Any] = {}

        if config.save_as:
            patch_vars[config.save_as] = approved

        return {
            "output": approved,
            "patch": (
                {
                    "vars": patch_vars,
                }
                if patch_vars
                else {}
            ),
            "meta": {
                "approved": approved,
            },
        }


NODE_TYPE = "human.approval"
NODE_CLS = HumanApprovalNode
CONFIG_MODEL = HumanApprovalConfig
