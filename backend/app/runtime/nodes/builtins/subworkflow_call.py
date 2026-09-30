from __future__ import annotations

import copy
from typing import Any, Dict

from app.runtime.nodes.types import NodeRunResult, RuntimeContext
from app.runtime.nodes.configs import SubworkflowCallConfig
from app.runtime.engine.executor import execute_workflow_dag


def _find_single_trigger_id(workflow: Dict[str, Any]) -> str | None:
    """
    Return the only trigger.message node id in a child workflow.

    If the child workflow has zero or multiple triggers, return None.

    Example:
        trigger_id = _find_single_trigger_id(workflow)

        if trigger_id:
            ...
    """
    triggers = []
    for n in workflow.get("nodes") or []:
        if (n.get("data") or {}).get("nodeType") == "trigger.message":
            triggers.append(n.get("id"))
    return triggers[0] if len(triggers) == 1 else None


def _inject_trigger_input(workflow: Dict[str, Any], msg: str) -> Dict[str, Any]:
    """
    Deep-copy child workflow and inject message into its trigger.message node.

    This avoids mutating the original configured child workflow.

    Example:
        child_wf = _inject_trigger_input(config.workflow, "hello")

        # child_wf trigger.message data.input == "hello"
    """
    wf = copy.deepcopy(workflow)
    trig_id = _find_single_trigger_id(wf)
    if not trig_id:
        return wf

    for n in wf.get("nodes") or []:
        if n.get("id") == trig_id:
            n.setdefault("data", {})
            n["data"]["input"] = msg
            break
    return wf


class SubworkflowCallNode:
    """
    Node that executes an inline child workflow.

    This enables workflow composition:
        parent workflow
            -> subworkflow.call
                -> child workflow
            -> continue parent workflow

    Input source:
        - state.last
        - state.vars[input_key]

    The input is injected into the child trigger.message node.

    If child workflow fails:
        this node raises RuntimeError, causing parent workflow to fail.

    If include_child_meta=True:
        child meta is attached to this node's meta.
    """

    async def run(
        self, ctx: RuntimeContext, state: Dict[str, Any], config: SubworkflowCallConfig
    ) -> NodeRunResult:
        vars_ = state.get("vars") or {}

        if config.input_from == "vars":
            msg = vars_.get(config.input_key, "")
        else:
            msg = state.get("last", "")

        msg = "" if msg is None else str(msg)

        child_wf = _inject_trigger_input(config.workflow, msg)

        # IMPORTANT: strict=True validates child too; no repo required.
        result = await execute_workflow_dag(
            ctx=ctx,
            workflow=child_wf,
            message=msg,
            strict=True,
            resume_workflow_run_id=None,
        )

        # If child failed, bubble up as node error (so parent run fails deterministically)
        if (result.get("meta") or {}).get("status") not in {"ok", "paused"}:
            raise RuntimeError(
                f"child_workflow_failed: {(result.get('meta') or {}).get('error') or result.get('meta')}"
            )

        out = result.get("answer")

        patch: Dict[str, Any] = {"last": out}

        if config.save_as:
            patch["vars"] = {config.save_as: out}

        meta: Dict[str, Any] = {}
        if config.include_child_meta:
            meta["child_meta"] = result.get("meta")

        return {"patch": patch, "output": out, "meta": meta}
