from __future__ import annotations

import os
from dataclasses import dataclass

"""
Customer Service AI Context Policy

IMPORTANT:

This policy exists to prevent model-facing services from loading
unbounded conversation history.

Historically several services loaded:

    conversation.messages

and then sorted/scanned the entire conversation in memory.

That approach becomes expensive as conversations grow and causes:

- unnecessary database load
- excessive memory usage
- large prompt construction costs
- unpredictable AI token consumption

All AI-facing features should obtain message context through
ConversationRepository.list_recent_context_messages(...)
or other bounded repository methods and then apply this policy.

Examples:

- AI Reply Compose
- AI Reply Regenerate
- Agent Assist
- Conversation Intelligence
- Conversation Summary
- Future AI agents

Do not use full conversation.message collections when building
AI prompts unless there is a very specific reason and the behavior
is intentionally documented.

This policy is the single source of truth for AI context sizing.
"""


@dataclass(frozen=True)
class CustomerServiceAIContextPolicy:
    recent_message_limit: int = 30
    max_context_chars: int = 6000
    intelligence_scan_message_limit: int = 80
    include_internal_notes: bool = False

    @classmethod
    def from_env(cls) -> "CustomerServiceAIContextPolicy":
        return cls(
            recent_message_limit=_env_int("TAJERAN_CS_AI_RECENT_MESSAGE_LIMIT", 30),
            max_context_chars=_env_int("TAJERAN_CS_AI_MAX_CONTEXT_CHARS", 6000),
            intelligence_scan_message_limit=_env_int(
                "TAJERAN_CS_AI_INTELLIGENCE_SCAN_MESSAGE_LIMIT",
                80,
            ),
            include_internal_notes=_env_bool(
                "TAJERAN_CS_AI_INCLUDE_INTERNAL_NOTES",
                False,
            ),
        )

    def trim_text(self, text: str) -> str:
        if len(text) <= self.max_context_chars:
            return text
        return text[-self.max_context_chars :]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
