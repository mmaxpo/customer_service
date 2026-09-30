from __future__ import annotations

from app.runtime.nodes.registry import register_node

from .nodes import (
    ShopifyGetOrderConfig,
    ShopifyGetOrderNode,
    ShopifyOrderActionConfig,
    ShopifyOrderActionNode,
)


def register_shopify_nodes() -> None:
    """Register legacy/runtime nodes owned by Shopify."""

    register_node(
        "shopify.get_order",
        ShopifyGetOrderNode,
        ShopifyGetOrderConfig,
        title="Shopify Get Order",
        category="data",
        group="Data",
        domain="shopify",
        discovery_id="shopify.get_order",
    )

    register_node(
        "shopify.order_action",
        ShopifyOrderActionNode,
        ShopifyOrderActionConfig,
        title="Shopify Order Action",
        category="platform",
        group="Platform",
        domain="shopify",
        risk_level="sensitive",
        side_effect=True,
        replay_policy="skip",
        discovery_id="shopify.order_action",
    )


__all__ = [
    "register_shopify_nodes",
]
