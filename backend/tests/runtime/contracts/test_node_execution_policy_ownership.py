from __future__ import annotations

from app.node_registration import (
    register_application_nodes,
)
from app.runtime.engine.idempotency import (
    is_side_effect_node,
)
from app.runtime.engine.replay_safety import (
    node_replay_policy,
)
from app.runtime.nodes.registry.core import (
    NODE_REGISTRY,
    get_node,
    register_node,
)


class _TestNode:
    pass


def _node(node_type: str) -> dict:
    return {
        "id": "node",
        "data": {
            "nodeType": node_type,
        },
    }


def test_registered_policy_drives_generic_runtime_safety() -> None:
    snapshot = dict(NODE_REGISTRY)

    try:
        NODE_REGISTRY.clear()

        register_node(
            "test.owner_side_effect",
            _TestNode,
            side_effect=True,
            replay_policy="skip",
        )

        node = _node(
            "test.owner_side_effect"
        )

        assert is_side_effect_node(node) is True
        assert node_replay_policy(node) == "skip"
    finally:
        NODE_REGISTRY.clear()
        NODE_REGISTRY.update(snapshot)


def test_unknown_node_defaults_to_safe_generic_policy() -> None:
    node = _node(
        "test.unregistered_safe_node"
    )

    assert is_side_effect_node(node) is False
    assert node_replay_policy(node) == "run"


def test_explicit_workflow_policy_still_takes_precedence() -> None:
    snapshot = dict(NODE_REGISTRY)

    try:
        NODE_REGISTRY.clear()

        register_node(
            "test.owner_side_effect",
            _TestNode,
            side_effect=True,
            replay_policy="skip",
        )

        node = {
            "id": "node",
            "data": {
                "nodeType": "test.owner_side_effect",
                "replay_policy": "run",
            },
        }

        # Side-effect status remains owner-defined for idempotency,
        # while an explicit workflow replay policy retains the
        # existing replay override behavior.
        assert is_side_effect_node(node) is True
        assert node_replay_policy(node) == "run"
    finally:
        NODE_REGISTRY.clear()
        NODE_REGISTRY.update(snapshot)


def test_real_node_owners_declare_current_side_effects() -> None:
    snapshot = dict(NODE_REGISTRY)

    try:
        NODE_REGISTRY.clear()

        register_application_nodes()

        expected = {
            "knowledge.ingest",
            "platform.job.enqueue",
            "reply.customer_chat",
            "customer_service.record_support_outcome",
            "shopify.order_action",
        }

        for node_type in expected:
            registration = get_node(
                node_type
            )

            assert (
                registration.side_effect
                is True
            )
            assert (
                registration.replay_policy
                == "skip"
            )

            node = _node(node_type)

            assert (
                is_side_effect_node(node)
                is True
            )
            assert (
                node_replay_policy(node)
                == "skip"
            )
    finally:
        NODE_REGISTRY.clear()
        NODE_REGISTRY.update(snapshot)
