# app/runtime/nodes/executor.py

from __future__ import annotations
import asyncio
from typing import Any, Tuple, Optional
from app.runtime.nodes.registry import get_node, parse_node_config
from app.runtime.state.patch import merge_patch
from app.runtime.utils.template import render_template


def _extract_raw_config(node_def: dict) -> dict:
    """
    Extract raw node configuration from a React Flow node definition.

    React Flow stores custom node settings inside node_def["data"]. This function
    returns a shallow copy so later rendering/parsing does not mutate the original
    node definition.

    Example:
        node_def = {"id": "n1", "data": {"nodeType": "llm.generate", "prompt": "Hi"}}
        config = _extract_raw_config(node_def)

        assert config["nodeType"] == "llm.generate"
    """
    return dict(node_def.get("data") or {})


def get_node_identity(node_def: dict) -> tuple[str | None, str]:
    """
    Return node id and node type, or fail if nodeType is missing.

    Every executable workflow node must have:
        node_def["data"]["nodeType"]

    Args:
        node_def: React Flow node definition.

    Returns:
        tuple[str | None, str]:
            node_id and node_type.

    Raises:
        ValueError: If data.nodeType is missing.

    Example:
        node_id, node_type = get_node_identity({
            "id": "kb1",
            "data": {"nodeType": "kb.search"},
        })

        assert node_id == "kb1"
        assert node_type == "kb.search"
    """
    node_id = node_def.get("id")
    node_type = (node_def.get("data") or {}).get("nodeType")

    if not node_type:
        raise ValueError(f"Node {node_id} missing data.nodeType")

    return node_id, node_type


def prepare_node_config(*, node_type: str, node_def: dict, state: dict):
    """
    Extract, template-render, and parse node configuration.

    This turns raw React Flow node.data into a validated config object.

    Steps:
        1. Extract raw config from node_def["data"].
        2. Render {{ variable }} templates using state["vars"].
        3. Parse rendered config through the registered Pydantic schema.

    Returns:
        tuple:
            raw_config: Original node.data copy.
            rendered_config: Template-rendered config dict.
            parsed_config: Pydantic config model or parsed config object.

    Example:
        state = {"vars": {"customer_name": "Mehdi"}}
        node_def = {
            "data": {
                "nodeType": "llm.generate",
                "prompt": "Hello {{ customer_name }}",
            }
        }

        raw, rendered, config = prepare_node_config(
            node_type="llm.generate",
            node_def=node_def,
            state=state,
        )

        assert rendered["prompt"] == "Hello Mehdi"
    """
    raw_config = _extract_raw_config(node_def)
    vars_ = state.get("vars") or {}
    rendered_config = render_template(raw_config, vars_)
    parsed_config = parse_node_config(node_type, rendered_config)
    return raw_config, rendered_config, parsed_config


def create_node_context(ctx, node_def: dict, node_data: Optional[dict]) -> NodeCtx:
    """
    Create a per-node context wrapper.

    Each node receives its own node_data while still being able to access the
    shared RuntimeContext through attribute forwarding.

    This prevents concurrency bugs when multiple nodes run in parallel.

    Example:
        nctx = create_node_context(ctx, node_def, node_data={"x": 1})

        assert nctx.node_data == {"x": 1}
        # nctx.user_id still resolves from base ctx
    """
    resolved_node_data = (
        node_data if node_data is not None else (node_def.get("data") or {})
    )
    return NodeCtx(ctx, resolved_node_data)


def get_node_execution_settings(
    config,
    rendered_config: dict,
) -> tuple[int | None, int, int]:
    """
    Read timeout and retry settings for node execution.

    Settings may come from either:
        - parsed config object
        - rendered raw config dict

    Fallback to rendered_config is important because some node schemas do not
    explicitly define timeout_ms/retries fields, but node.data may still include
    them.

    Returns:
        tuple:
            timeout_ms: Optional timeout in milliseconds.
            retries: Number of retry attempts after first failure.
            backoff_ms: Delay between retries in milliseconds.

    Example:
        timeout_ms, retries, backoff_ms = get_node_execution_settings(
            config,
            {"timeout_ms": 5000, "retries": 2, "retry_backoff_ms": 100},
        )

        assert timeout_ms == 5000
        assert retries == 2
    """
    timeout_ms = getattr(config, "timeout_ms", None) or rendered_config.get(
        "timeout_ms"
    )
    retries = int(getattr(config, "retries", rendered_config.get("retries", 0)) or 0)
    backoff_ms = int(
        getattr(config, "retry_backoff_ms", rendered_config.get("retry_backoff_ms", 0))
        or 0
    )
    return timeout_ms, retries, backoff_ms


async def run_node_once(
    *,
    node,
    nctx: NodeCtx,
    state: dict,
    config,
    node_id: str | None,
    node_type: str,
    timeout_ms: int | float | None,
) -> dict:
    """
    Execute node.run() once, optionally with a timeout.

    This function does not retry. Retry behavior is handled by
    run_node_with_retries().

    Args:
        node: Node instance.
        nctx: Per-node context.
        state: State snapshot passed into node.
        config: Parsed node config.
        node_id: Node id for error messages.
        node_type: Node type for error messages.
        timeout_ms: Optional timeout in milliseconds.

    Raises:
        TimeoutError: If node.run() exceeds timeout_ms.

    Example:
        result = await run_node_once(
            node=node,
            nctx=nctx,
            state=state,
            config=config,
            node_id="slow_node",
            node_type="test.sleep",
            timeout_ms=1000,
        )
    """
    if timeout_ms:
        try:
            return await asyncio.wait_for(
                node.run(nctx, state, config),
                timeout=float(timeout_ms) / 1000.0,
            )
        except asyncio.TimeoutError as te:
            raise TimeoutError(
                f"node_timeout: {node_id} ({node_type}) after {timeout_ms}ms"
            ) from te

    return await node.run(nctx, state, config)


async def run_node_with_retries(
    *,
    node,
    nctx: NodeCtx,
    state: dict,
    config,
    node_id: str | None,
    node_type: str,
    timeout_ms: int | float | None,
    retries: int,
    backoff_ms: int,
) -> dict:
    """
    Execute a node with timeout and retry policy.

    The first execution counts as attempt 1. If retries=2, the node may run up
    to 3 total attempts.

    Args:
        retries: Number of retries after the first failed attempt.
        backoff_ms: Delay between failed attempts.

    Raises:
        Exception: Re-raises the last node error after retries are exhausted.

    Example:
        result = await run_node_with_retries(
            node=node,
            nctx=nctx,
            state=state,
            config=config,
            node_id="web_search",
            node_type="web.search",
            timeout_ms=5000,
            retries=2,
            backoff_ms=250,
        )
    """
    attempt = 0

    while True:
        attempt += 1

        try:
            return await run_node_once(
                node=node,
                nctx=nctx,
                state=state,
                config=config,
                node_id=node_id,
                node_type=node_type,
                timeout_ms=timeout_ms,
            )
        except Exception:
            if attempt > retries + 1:
                raise

            if backoff_ms > 0:
                await asyncio.sleep(backoff_ms / 1000.0)


class NodeCtx:
    """
    Per-node context wrapper.

    NodeCtx gives each node its own node_data while forwarding all other
    attributes to the shared RuntimeContext.

    Why this exists:
        Parallel nodes must not mutate shared ctx.node_data.

    Example:
        nctx = NodeCtx(base_ctx=ctx, node_data={"query": "refund policy"})

        assert nctx.node_data["query"] == "refund policy"
        # nctx.user_id is resolved from ctx.user_id through __getattr__
    """

    def __init__(self, base_ctx: Any, node_data: dict):
        """
        Store the shared base context and per-node data.

        Args:
            base_ctx: Original RuntimeContext.
            node_data: Data specific to this node execution.
        """
        self._base = base_ctx
        self.node_data = node_data or {}

    def __getattr__(self, name: str) -> Any:
        """
        Forward missing attributes to the base RuntimeContext.

        Example:
            nctx.db
            # resolves to nctx._base.db
        """
        return getattr(self._base, name)


async def call_node(
    ctx,
    node_def: dict,
    state: dict,
    *,
    node_data: Optional[dict] = None,
) -> dict:
    """
    Execute one workflow node and return its raw result.

    This function does NOT merge the result into RunState. The engine controls
    merge order so parallel execution remains deterministic.

    Flow:
        1. Read node id and node type.
        2. Get registered node class.
        3. Render and parse node config.
        4. Create node instance.
        5. Create per-node context.
        6. Read timeout/retry settings.
        7. Execute node with retry policy.
        8. Validate result is a dict.

    Args:
        ctx: RuntimeContext.
        node_def: React Flow node definition.
        state: Stable state snapshot.
        node_data: Optional per-node execution data, such as join inputs.

    Returns:
        dict: Raw node result.

    Expected result shape:
        {
            "output": ...,
            "patch": {...},
            "meta": {...},
            "route": optional,
            "status": optional,
        }

    Example:
        result = await call_node(ctx, node_def, state_snapshot)

        assert isinstance(result, dict)
        assert "output" in result
    """
    node_id, node_type = get_node_identity(node_def)

    reg = get_node(node_type)

    raw_config, rendered_config, config = prepare_node_config(
        node_type=node_type,
        node_def=node_def,
        state=state,
    )

    node = reg.node_cls()

    nctx = create_node_context(ctx, node_def, node_data)

    timeout_ms, retries, backoff_ms = get_node_execution_settings(
        config,
        rendered_config,
    )
    result = await run_node_with_retries(
        node=node,
        nctx=nctx,
        state=state,
        config=config,
        node_id=node_id,
        node_type=node_type,
        timeout_ms=timeout_ms,
        retries=retries,
        backoff_ms=backoff_ms,
    )

    if not isinstance(result, dict):
        raise ValueError(f"Node {node_id} returned non-dict result")

    return result


def apply_node_result(state: dict, node_def: dict, result: dict) -> dict:
    """
    Merge a raw node result into RunState.

    This function is called by the engine after node execution completes.

    It updates:
        - state via result["patch"]
        - state["last"], unless result["update_last"] is False
        - state["results"][node_id]
        - state["meta"]["node_meta_by_id"][node_id]
        - state["vars"][save_as] when configured

    Important:
        If patch["vars"] already contains save_as, this function does not
        overwrite it with output.

    Example:
        result = {
            "output": "Refund allowed",
            "patch": {"vars": {"intent": "refund"}},
            "meta": {"model": "gpt"},
        }

        state = apply_node_result(state, node_def, result)

        assert state["last"] == "Refund allowed"
        assert state["vars"]["intent"] == "refund"
        assert state["results"][node_def["id"]] == "Refund allowed"
    """
    node_id = node_def.get("id")
    raw_config = _extract_raw_config(node_def)

    node_type = (node_def.get("data") or {}).get("nodeType")
    config = parse_node_config(node_type, raw_config) if node_type else raw_config

    patch = result.get("patch") or {}
    output = result.get("output", None)
    update_last = result.get("update_last", True)

    if not isinstance(update_last, bool):
        raise ValueError(
            f"Node {node_id} returned non-boolean update_last"
        )

    # 1) Merge patch first (patch may write vars[save_as] for artifact nodes)
    state = merge_patch(state, patch)

    # Most nodes advance the workflow's implicit value through state["last"].
    # Context/metadata nodes may opt out while still exposing their output in
    # state["results"] and vars[save_as].
    if update_last:
        state["last"] = output

    # --- store results/meta into RunState ---
    state.setdefault("results", {})
    if node_id:
        state["results"][node_id] = output

    state.setdefault("meta", {})
    state["meta"].setdefault("node_meta_by_id", {})
    if node_id:
        state["meta"]["node_meta_by_id"][node_id] = result.get("meta") or {}

    # --- optional save_as ---
    save_as = getattr(config, "save_as", None) or raw_config.get("save_as")
    if save_as:
        # ✅ Do NOT overwrite if patch already set this var key
        patch_vars = patch.get("vars") or {}
        if save_as not in patch_vars:
            state.setdefault("vars", {})[save_as] = output

    return state


async def run_node(ctx, node_def: dict, state: dict) -> Tuple[dict, dict]:
    """
    Backward-compatible sequential node runner.

    This helper executes a node and immediately applies the node result to state.
    It is useful for older sequential code paths or simple tests.

    New DAG execution should prefer:
        call_node()
        apply_node_result()

    Returns:
        tuple[dict, dict]:
            updated state
            raw node result

    Example:
        state, result = await run_node(ctx, node_def, state)
    """
    result = await call_node(ctx, node_def, state)
    state = apply_node_result(state, node_def, result)
    return state, result
