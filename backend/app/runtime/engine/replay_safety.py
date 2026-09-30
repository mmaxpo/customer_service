from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableSet
from typing import Any

from app.runtime.nodes.registry.core import get_node


EmitFn = Callable[[dict[str, Any]], Awaitable[None]]


SKIP_REPLAY_POLICIES = {
    "skip",
    "side_effect",
    "dangerous",
    "no_replay",
    "never",
}


def is_replay_enabled(state: dict[str, Any]) -> bool:
    replay = (state.get("meta") or {}).get("replay") or {}
    return bool(replay.get("enabled"))


def node_replay_policy(node_def: dict[str, Any]) -> str:
    data = node_def.get("data") or {}

    explicit = (
        data.get("replay_policy") or data.get("replayPolicy") or data.get("replay")
    )

    if isinstance(explicit, dict):
        explicit = explicit.get("policy") or explicit.get("mode")

    if explicit is not None:
        return str(explicit).strip().lower()

    if (
        data.get("replay_safe") is False
        or data.get("replaySafe") is False
    ):
        return "skip"

    node_type = str(
        data.get("nodeType")
        or data.get("node_type")
        or ""
    ).strip()

    if not node_type:
        return "run"

    try:
        registration = get_node(node_type)
    except ValueError:
        return "run"

    return str(
        registration.replay_policy or "run"
    ).strip().lower()


def is_replay_blocked_node(node_def: dict[str, Any]) -> bool:
    return node_replay_policy(node_def) in SKIP_REPLAY_POLICIES


async def skip_replay_blocked_nodes(
    *,
    ready: list[str],
    nodes_by_id: dict[str, dict[str, Any]],
    state: dict[str, Any],
    started: set[str],
    finished: MutableSet[str],
    skipped: MutableSet[str],
    emit: EmitFn,
) -> bool:
    """
    During replay/debug execution, block nodes that can produce external side effects.

    This prevents snapshot replay from repeating nodes whose
    owner-defined or workflow-defined replay policy blocks replay.

    Returns True when at least one ready node was skipped.
    """
    if not is_replay_enabled(state):
        return False

    changed = False

    for node_id in list(ready):
        if node_id in started or node_id in finished:
            continue

        node_def = nodes_by_id[node_id]

        if not is_replay_blocked_node(node_def):
            continue

        data = node_def.get("data") or {}
        node_type = data.get("nodeType")

        skipped.add(node_id)
        finished.add(node_id)

        # Preserve any existing output from the snapshot if present, but do not invent output.
        state.setdefault("results", {})
        state["results"].setdefault(node_id, None)

        state.setdefault("meta", {})
        state["meta"].setdefault("replay", {})
        state["meta"]["replay"].setdefault("skipped_side_effect_nodes", [])
        state["meta"]["replay"]["skipped_side_effect_nodes"].append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "policy": node_replay_policy(node_def),
            }
        )

        await emit(
            {
                "event": "node_skip",
                "node_id": node_id,
                "node_type": node_type,
                "reason": "replay_side_effect_blocked",
            }
        )

        changed = True

    return changed
