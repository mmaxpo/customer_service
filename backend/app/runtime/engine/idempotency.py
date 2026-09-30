from __future__ import annotations

import hashlib
from typing import Any

from app.runtime.nodes.registry.core import get_node


SIDE_EFFECT_REPLAY_POLICIES = {
    "skip",
    "side_effect",
    "dangerous",
    "no_replay",
    "never",
}


def _explicit_replay_policy(data: dict[str, Any]) -> str | None:
    replay_policy = (
        data.get("replay_policy")
        or data.get("replayPolicy")
        or data.get("replay")
    )

    if isinstance(replay_policy, dict):
        replay_policy = (
            replay_policy.get("policy")
            or replay_policy.get("mode")
        )

    if replay_policy is None:
        return None

    return str(replay_policy).strip().lower()


def _registered_node_policy(
    node_type: str,
) -> tuple[bool, str]:
    if not node_type:
        return False, "run"

    try:
        registration = get_node(node_type)
    except ValueError:
        return False, "run"

    return (
        bool(registration.side_effect),
        str(
            registration.replay_policy or "run"
        ).strip().lower(),
    )


def is_side_effect_node(
    node_def: dict[str, Any],
) -> bool:
    data = node_def.get("data") or {}
    node_type = str(
        data.get("nodeType")
        or data.get("node_type")
        or ""
    ).strip()

    if (
        data.get("side_effect") is True
        or data.get("sideEffect") is True
    ):
        return True

    explicit_replay_policy = (
        _explicit_replay_policy(data)
    )

    if (
        explicit_replay_policy
        in SIDE_EFFECT_REPLAY_POLICIES
    ):
        return True

    registered_side_effect, registered_replay_policy = (
        _registered_node_policy(node_type)
    )

    return (
        registered_side_effect
        or registered_replay_policy
        in SIDE_EFFECT_REPLAY_POLICIES
    )


def build_node_idempotency_key(
    *,
    state: dict[str, Any],
    node_id: str,
    node_type: str | None,
) -> str:
    """
    Build a stable idempotency key for one external side-effect node.

    The key is stable across:
      - node retry attempts
      - worker retry of the same workflow run
      - crash after external success but before local persist

    The key intentionally does NOT include retry attempt number.
    """
    workflow_run_id = str(
        state.get("workflow_run_id") or ""
    )
    user_id = str(
        (state.get("meta") or {}).get("user_id")
        or ""
    )
    raw = (
        f"tajeran:v1:{user_id}:"
        f"{workflow_run_id}:{node_id}:"
        f"{node_type or ''}"
    )
    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:32]
    return f"wfnode_{digest}"
