from __future__ import annotations

from enum import StrEnum
from typing import Literal


class TokenBudgetMode(StrEnum):
    CHEAP = "cheap"
    LEAN = "lean"
    BALANCED = "balanced"
    QUALITY = "quality"


AgentRole = Literal[
    "worker",
    "decision",
    "final",
    "router",
    "planner",
    "evaluator",
    "tool_executor",
    "supervisor",
]


ROLE_OUTPUT_TOKEN_LIMITS: dict[str, dict[TokenBudgetMode, int]] = {
    "worker": {
        TokenBudgetMode.CHEAP: 120,
        TokenBudgetMode.LEAN: 300,
        TokenBudgetMode.BALANCED: 600,
        TokenBudgetMode.QUALITY: 900,
    },
    "decision": {
        TokenBudgetMode.CHEAP: 50,
        TokenBudgetMode.LEAN: 120,
        TokenBudgetMode.BALANCED: 250,
        TokenBudgetMode.QUALITY: 400,
    },
    "final": {
        TokenBudgetMode.CHEAP: 300,
        TokenBudgetMode.LEAN: 500,
        TokenBudgetMode.BALANCED: 700,
        TokenBudgetMode.QUALITY: 1000,
    },
    "router": {
        TokenBudgetMode.CHEAP: 30,
        TokenBudgetMode.LEAN: 60,
        TokenBudgetMode.BALANCED: 100,
        TokenBudgetMode.QUALITY: 180,
    },
    "planner": {
        TokenBudgetMode.CHEAP: 250,
        TokenBudgetMode.LEAN: 500,
        TokenBudgetMode.BALANCED: 900,
        TokenBudgetMode.QUALITY: 1200,
    },
    "evaluator": {
        TokenBudgetMode.CHEAP: 80,
        TokenBudgetMode.LEAN: 160,
        TokenBudgetMode.BALANCED: 300,
        TokenBudgetMode.QUALITY: 500,
    },
    "tool_executor": {
        TokenBudgetMode.CHEAP: 80,
        TokenBudgetMode.LEAN: 200,
        TokenBudgetMode.BALANCED: 400,
        TokenBudgetMode.QUALITY: 700,
    },
    "supervisor": {
        TokenBudgetMode.CHEAP: 120,
        TokenBudgetMode.LEAN: 300,
        TokenBudgetMode.BALANCED: 600,
        TokenBudgetMode.QUALITY: 900,
    },
}

DEFAULT_ROLE = "worker"
DEFAULT_MODE = TokenBudgetMode.BALANCED
ABSOLUTE_MAX_OUTPUT_TOKENS = 2000


def normalize_budget_mode(value: str | None) -> TokenBudgetMode:
    if not value:
        return DEFAULT_MODE

    try:
        return TokenBudgetMode(value)
    except ValueError:
        return DEFAULT_MODE


def resolve_max_output_tokens(
    *,
    role: str | None,
    requested_max_output_tokens: int | None = None,
    token_budget_mode: str | None = None,
) -> int:
    safe_role = role or DEFAULT_ROLE
    mode = normalize_budget_mode(token_budget_mode)

    role_limits = ROLE_OUTPUT_TOKEN_LIMITS.get(
        safe_role,
        ROLE_OUTPUT_TOKEN_LIMITS[DEFAULT_ROLE],
    )

    role_limit = role_limits[mode]

    if requested_max_output_tokens is None:
        return role_limit

    try:
        requested = int(requested_max_output_tokens)
    except Exception:
        return role_limit

    if requested <= 0:
        return role_limit

    return min(requested, role_limit, ABSOLUTE_MAX_OUTPUT_TOKENS)


def estimate_tokens(text: str) -> int:

    if not text:
        return 0

    try:
        import tiktoken

        try:
            enc = tiktoken.get_encoding("cl100k_base")

        except Exception:
            enc = tiktoken.encoding_for_model("gpt-4o-mini")

        return len(enc.encode(text))

    except Exception:
        # Safe fallback: rough estimate, never crash workflow.

        # English average: ~4 chars per token.

        return max(1, len(text) // 4)
