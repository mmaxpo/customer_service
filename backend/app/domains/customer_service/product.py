from __future__ import annotations

from typing import Final


PRODUCT_ID: Final = "shopify_customer_service"
SELLABLE_PROMISE: Final = (
    "AI operations customer service for Shopify stores, supporting email and "
    "website chat."
)
SELLABLE_CHANNELS: Final = ("email", "website_chat")


def customer_service_product_contract() -> dict:
    """The public launch contract. Experimental adapters stay out of this response."""
    return {
        "id": PRODUCT_ID,
        "promise": SELLABLE_PROMISE,
        "commerce_provider": "shopify",
        "channels": list(SELLABLE_CHANNELS),
        "capabilities": [
            "unified_inbox",
            "workspace_knowledge",
            "ai_reply_drafts",
            "multilingual_intelligence",
            "merchant_autopilot",
            "human_approvals",
            "shopify_order_operations",
            "automation_activity",
            "helpdesk_bulk_actions",
            "reply_drafts_and_signatures",
            "spam_phishing_quarantine",
            "business_value_analytics",
            "proactive_playbooks",
            "verification_and_repair",
            "learning_insights",
            "sla_and_routing",
            "billing",
        ],
        "autopilot_modes": [
            "recommend_only",
            "draft_reply",
            "auto_send_safe",
            "require_approval",
            "never_automate",
        ],
        "hidden_providers": [
            "whatsapp",
            "instagram",
            "facebook",
            "generic_omnichannel",
        ],
        "status": "sellable",
    }
