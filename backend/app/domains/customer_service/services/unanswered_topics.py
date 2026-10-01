"""
Automations / Knowledge: what customers asked this week that the automation
handed to the team, grouped by topic. One AI call groups the messages; the
result is kept for a few hours in the chat widget settings (`meta`), together
with the topics the team dismissed.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.providers.llm.factory import build_generate_llm_client
from app.core.providers.llm.resilience import LLMProviderError
from app.domains.customer_service.models import CustomerChatWidgetSettings
from app.domains.customer_service.services.automation_studio import _parse_json
from app.domains.customer_service.services.live_monitor import LiveMonitorService

DAYS = 7
MIN_QUESTIONS = 3
REFRESH_AFTER = timedelta(hours=6)
MAX_MESSAGES = 200

SYSTEM = (
    "You group customer-support questions by what the customer wants to know. "
    'Reply with JSON only: {"topics": [{"topic": "<2-4 lowercase words, e.g. gift wrapping>", '
    '"messages": [<numbers of the messages in this group>]}]}. '
    "Put a message in at most one group. Leave out messages that are greetings, "
    "only an order number, or unclear."
)


class UnansweredTopicsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _settings(self, workspace_id: UUID):
        return await self.db.scalar(
            select(CustomerChatWidgetSettings).where(
                CustomerChatWidgetSettings.user_id == workspace_id
            )
        )

    async def topics(self, *, workspace_id: UUID) -> dict:
        settings = await self._settings(workspace_id)
        if settings is None:
            return {"days": DAYS, "topics": []}
        stored = dict((settings.meta or {}).get("unanswered_topics") or {})
        now = datetime.now(timezone.utc)

        generated_at = stored.get("generated_at")
        if not generated_at or now - datetime.fromisoformat(generated_at) > REFRESH_AFTER:
            fresh = await self._group(workspace_id)
            # Keep the last result when the AI provider is down.
            if fresh is not None:
                stored = {**stored, "generated_at": now.isoformat(), "topics": fresh}
                settings.meta = {**(settings.meta or {}), "unanswered_topics": stored}
                flag_modified(settings, "meta")
                await self.db.commit()

        dismissed = set(stored.get("dismissed") or [])
        return {
            "days": DAYS,
            "topics": [t for t in stored.get("topics") or [] if t["topic"] not in dismissed],
        }

    async def dismiss(self, *, workspace_id: UUID, topic: str) -> dict:
        settings = await self._settings(workspace_id)
        if settings is not None:
            stored = dict((settings.meta or {}).get("unanswered_topics") or {})
            stored["dismissed"] = sorted({*(stored.get("dismissed") or []), topic})
            settings.meta = {**(settings.meta or {}), "unanswered_topics": stored}
            flag_modified(settings, "meta")
            await self.db.commit()
        return await self.topics(workspace_id=workspace_id)

    async def _group(self, workspace_id: UUID) -> list[dict] | None:
        rows = await LiveMonitorService(self.db).activity(
            workspace_id=workspace_id, days=DAYS, limit=1000, outcome="handed_over"
        )
        # A hand-over because the AI provider was down says nothing about the topic.
        messages = list(
            dict.fromkeys(
                (row["customer_message"] or "").strip()
                for row in rows
                if "AI provider" not in (row["reason"] or "")
            )
        )
        messages = [m for m in messages if m][:MAX_MESSAGES]
        if len(messages) < MIN_QUESTIONS:
            return []

        try:
            reply = await build_generate_llm_client().generate(
                prompt="Messages:\n"
                + "\n".join(f"{i + 1}. {json.dumps(m[:300], ensure_ascii=False)}" for i, m in enumerate(messages)),
                system=SYSTEM,
                max_tokens=3000,
            )
            parsed = _parse_json(reply.text)
        except (LLMProviderError, ValueError):
            return None

        topics = []
        for group in parsed.get("topics") or []:
            numbers = {n for n in group.get("messages") or [] if isinstance(n, int) and 1 <= n <= len(messages)}
            name = str(group.get("topic") or "").strip().lower()
            if name and len(numbers) >= MIN_QUESTIONS:
                topics.append(
                    {
                        "topic": name,
                        "count": len(numbers),
                        "examples": [messages[n - 1][:200] for n in sorted(numbers)[:3]],
                    }
                )
        return sorted(topics, key=lambda t: -t["count"])
