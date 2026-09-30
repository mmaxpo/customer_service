from __future__ import annotations


PLAN_CATALOG = {
    "starter": {
        "shopify_name": "Tajeran Starter",
        "amount": "49.00",
        "currency": "USD",
        "interval": "EVERY_30_DAYS",
        "entitlements": {
            "agent_replies": True,
            "attachments": True,
            "saved_views": True,
            "monthly_conversations": 1000,
            "members": 3,
            "autopilot_safe_replies": False,
        },
    },
    "growth": {
        "shopify_name": "Tajeran Growth",
        "amount": "149.00",
        "currency": "USD",
        "interval": "EVERY_30_DAYS",
        "entitlements": {
            "agent_replies": True,
            "attachments": True,
            "saved_views": True,
            "monthly_conversations": 5000,
            "members": 10,
            "autopilot_safe_replies": True,
        },
    },
    "pro": {
        "shopify_name": "Tajeran Pro",
        "amount": "399.00",
        "currency": "USD",
        "interval": "EVERY_30_DAYS",
        "entitlements": {
            "agent_replies": True,
            "attachments": True,
            "saved_views": True,
            "monthly_conversations": 20000,
            "members": 30,
            "autopilot_safe_replies": True,
        },
    },
}


def plan_entitlements(plan: str) -> dict:
    definition = PLAN_CATALOG.get(plan)
    return dict(definition["entitlements"]) if definition else {}


def plan_from_shopify_name(name: str) -> str | None:
    return next(
        (key for key, value in PLAN_CATALOG.items() if value["shopify_name"] == name),
        None,
    )
