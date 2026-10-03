"""
Inbox: translate a conversation (the customer and the replies they got) into
the team's language, on request.
Nothing is stored; each request is one AI call.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.providers.llm.factory import build_generate_llm_client
from app.core.providers.llm.resilience import LLMProviderError
from app.domains.customer_service.services.automation_studio_json import parse_json
from app.tenancy.models import Workspace

MAX_MESSAGES = 20

SYSTEM = (
    "You translate the messages of a customer-support conversation for a support team. "
    "Reply with JSON only: "
    '{"language": "<English name of the language the customer wrote in>", '
    '"language_code": "<its ISO 639-1 code>", '
    '"translations": ["<translation of message 1>", "..."]}. '
    "Translate every message into the target language, in the same order, "
    "keeping names, order numbers and email addresses unchanged. "
    "If the messages are already in the target language, return an empty translations list."
)


class ConversationTranslationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def translate(self, *, workspace_id: UUID, conversation_id: UUID) -> dict:
        result = await self.db.execute(
            text(
                """
                SELECT body FROM (
                  SELECT m.body, m.created_at
                  FROM cs_conversation_messages m
                  JOIN cs_conversations c ON c.id = m.conversation_id
                  WHERE c.id = :conversation_id AND c.user_id = :workspace_id
                    AND lower(m.sender_type::text) IN ('customer', 'ai', 'agent')
                  ORDER BY m.created_at DESC
                  LIMIT :limit
                ) recent ORDER BY created_at
                """
            ),
            {"conversation_id": conversation_id, "workspace_id": workspace_id, "limit": MAX_MESSAGES},
        )
        messages = [body for (body,) in result if (body or "").strip()]
        if not messages:
            raise HTTPException(status_code=404, detail="No messages to translate.")

        workspace = await self.db.get(Workspace, workspace_id)
        target = (workspace.default_locale if workspace else None) or "en"

        try:
            reply = await build_generate_llm_client().generate(
                prompt=f"Target language code: {target}\n\nMessages:\n"
                + json.dumps(messages, ensure_ascii=False),
                system=SYSTEM,
                max_tokens=3000,
            )
            parsed = parse_json(reply.text)
        except LLMProviderError as exc:
            raise HTTPException(
                status_code=503,
                detail="Translation isn't available right now because the AI provider is not responding. Try again in a few minutes.",
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="The translation could not be read. Try again.") from exc

        translations = parsed.get("translations") or []
        code = str(parsed.get("language_code") or "").lower()
        same = code == target.split("-")[0].lower()
        if not same and len(translations) != len(messages):
            # A partial answer can't be matched to the messages it belongs to.
            raise HTTPException(status_code=502, detail="The translation came back incomplete. Try again.")
        return {
            "language": parsed.get("language"),
            "translated": not same,
            "translations": []
            if same
            else [
                {"original": original, "text": str(translated)}
                for original, translated in zip(messages, translations)
                if str(translated).strip() != original.strip()
            ],
        }
