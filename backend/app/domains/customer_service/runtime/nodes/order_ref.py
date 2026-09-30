from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExtractOrderRefConfig(BaseModel):
    node_type: Literal["customer_service.extract_order_ref"] = (
        "customer_service.extract_order_ref"
    )

    input_from: Literal["last", "vars", "config"] = Field(default="last")
    input_key: str = Field(default="input")
    text: str | None = None

    save_as: str = Field(default="order_ref")


class ExtractOrderRefNode:
    async def run(
        self,
        ctx,
        state: dict[str, Any],
        config: ExtractOrderRefConfig,
    ) -> dict[str, Any]:
        vars_ = state.get("vars") or {}

        if config.input_from == "config":
            raw = config.text
        elif config.input_from == "vars":
            raw = vars_.get(config.input_key)
        else:
            raw = state.get("last") or vars_.get("input")

        text = str(raw or "").strip()

        match = re.search(r"#\s*(\d{3,20})\b", text)
        if match is None:
            match = re.search(
                r"\border\s*(?:number|no\.?|#)?\s*(\d{3,20})\b", text, re.I
            )

        order_ref = f"#{match.group(1)}" if match else ""

        return {
            "output": order_ref,
            "patch": {
                "vars": {
                    config.save_as: order_ref,
                    "order_ref_found": bool(order_ref),
                },
                "last": order_ref,
            },
            "meta": {
                "order_ref": order_ref,
                "found": bool(order_ref),
            },
        }
