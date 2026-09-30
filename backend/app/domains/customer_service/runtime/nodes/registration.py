from __future__ import annotations

from app.runtime.nodes.registry import register_node

from .customer_chat import (
    CustomerChatReplyConfig,
    CustomerChatReplyNode,
)
from .customer_support_outcome import (
    CustomerSupportOutcomeProjectionConfig,
    CustomerSupportOutcomeProjectionNode,
)
from .customer_support_outcome_recording import (
    CustomerSupportOutcomeRecordingConfig,
    CustomerSupportOutcomeRecordingNode,
)
from .order_ref import (
    ExtractOrderRefConfig,
    ExtractOrderRefNode,
)


def register_customer_service_nodes() -> None:
    """Register workflow nodes owned by Customer Service."""

    register_node(
        "customer_service.extract_order_ref",
        ExtractOrderRefNode,
        ExtractOrderRefConfig,
        title="Extract Order Reference",
        category="data",
        group="Data",
        domain="customer_service",
        discovery_id="customer_service.extract_order_ref",
    )

    register_node(
        "reply.customer_chat",
        CustomerChatReplyNode,
        CustomerChatReplyConfig,
        title="Customer Chat Reply",
        category="output",
        group="Output",
        domain="customer_service",
        side_effect=True,
        replay_policy="skip",
        discovery_id="reply.customer_chat",
    )

    register_node(
        "customer_service.project_support_outcome",
        CustomerSupportOutcomeProjectionNode,
        CustomerSupportOutcomeProjectionConfig,
        title="Project Support Outcome",
        category="data",
        group="Data",
        domain="customer_service",
        discovery_id="customer_service.project_support_outcome",
    )

    register_node(
        "customer_service.record_support_outcome",
        CustomerSupportOutcomeRecordingNode,
        CustomerSupportOutcomeRecordingConfig,
        title="Record Support Outcome",
        category="data",
        group="Data",
        domain="customer_service",
        side_effect=True,
        replay_policy="skip",
        discovery_id="customer_service.record_support_outcome",
    )


__all__ = [
    "register_customer_service_nodes",
]
