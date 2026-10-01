"""
New workflows from a prompt: TCOS drafts a chat workflow from a typed request,
names it and proposes which messages it answers (keywords and an optional
topic). It is saved switched off; the owner edits it and turns it on.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.providers.llm.factory import build_generate_llm_client
from app.core.providers.llm.resilience import LLMProviderError
from app.domains.customer_service.models import CustomerServiceEventSubscription
from app.domains.customer_service.services.automation_studio import (
    AutomationStudioService,
    _catalog,
    _graph_view,
    _parse_json,
    _validate,
)

# Topics a new workflow may be limited to. Cancellations and damaged items
# always go to a person, so they are not offered.
NEW_WORKFLOW_TOPICS = ("general", "shipping", "refund")

NEW_WORKFLOW_SYSTEM = (
    "You name a new customer-chat workflow and decide which messages it answers. "
    'Reply with JSON only: {"name": "<2-5 words>", "description": "<one sentence>", '
    '"topic": "general" | "shipping" | "refund" | null, '
    '"keywords": ["<3-8 short lowercase words or phrases a customer would type about this subject>"]}. '
    "The workflow runs when a customer message contains any keyword. Prefer short "
    "word stems (for example 'gift wrap') over long phrases. Use topic null unless "
    "the subject is clearly only shipping or only refunds."
)

# The smallest useful chat workflow; a new workflow is drafted as a change to it.
STARTER_WORKFLOW = {
    "name": "New workflow",
    "nodes": [
        {"id": "trigger", "data": {"nodeType": "trigger.message"}},
        {"id": "load_conversation", "data": {"nodeType": "customer_service.load_conversation", "save_as": "conversation"}},
        {"id": "search_knowledge", "data": {"nodeType": "kb.search", "k": 3, "query": "", "artifact_as": "kb_results"}},
        {
            "id": "generate_reply",
            "data": {
                "nodeType": "llm.generate",
                "save_as": "reply",
                "system": "You are a helpful ecommerce support assistant. Use only the help articles provided for facts.",
                "prompt": (
                    "Customer message: {{input}}\n\nEarlier messages in this conversation:\n{{vars.conversation}}\n\n"
                    "Help article hits: {{vars.kb_results}}\n\n"
                    "Answer the customer message. Use ONLY the help articles for facts. Maximum 80 words.\n\n"
                    "If the help articles do not answer the question: say you don't have that information, and that "
                    "you have passed the question to the team, who will reply here.\n\n"
                    "Hand-off rule: add [HANDOFF] at the very end ONLY when your reply says that you passed this to "
                    "the team or that a team member will reply.\n\n{{vars.reply_language_rule}}"
                ),
                "provider_failure_fallback": "Our AI assistant is temporarily unavailable. A human support agent will review your message.",
            },
        },
        {
            "id": "reply_customer",
            "data": {
                "nodeType": "reply.customer_chat",
                "message_key": "reply",
                "message_from": "vars",
                "session_id_key": "session_id",
                "session_id_from": "extras",
            },
        },
        {"id": "response", "data": {"nodeType": "response"}},
    ],
    "edges": [
        {"source": "trigger", "target": "load_conversation"},
        {"source": "load_conversation", "target": "search_knowledge"},
        {"source": "search_knowledge", "target": "generate_reply"},
        {"source": "generate_reply", "target": "reply_customer"},
        {"source": "reply_customer", "target": "response"},
    ],
}


def _keywords(value: Any) -> list[str]:
    words = [str(item).strip().lower()[:40] for item in value or [] if str(item).strip()]
    return list(dict.fromkeys(words))[:12]


class NewWorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.studio = AutomationStudioService(db)

    async def draft_workflow(self, *, request: str) -> dict:
        """Draft a new chat workflow from a typed request. Nothing is saved."""
        catalog = _catalog()
        drafted = await self.studio._generate(base=STARTER_WORKFLOW, requests=[request], catalog=catalog)
        try:
            result = await build_generate_llm_client().generate(
                prompt=f"The store owner asked for this new workflow:\n{request}",
                system=NEW_WORKFLOW_SYSTEM,
                max_tokens=400,
            )
            routing = _parse_json(result.text)
        except LLMProviderError as exc:
            raise HTTPException(
                status_code=503,
                detail="TCOS can't draft a workflow right now because the AI provider is unavailable. Try again in a few minutes.",
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="TCOS could not draft this workflow. Try rephrasing it.") from exc

        topic = routing.get("topic")
        return {
            "name": str(routing.get("name") or "New workflow")[:120],
            "description": str(routing.get("description") or "")[:500],
            "topic": topic if topic in NEW_WORKFLOW_TOPICS else None,
            "keywords": _keywords(routing.get("keywords")),
            "workflow": drafted["workflow"],
            "graph": _graph_view(drafted["workflow"], catalog),
            "validation_errors": _validate(drafted["workflow"], catalog),
        }

    async def create_workflow(
        self,
        *,
        workspace_id: UUID,
        name: str,
        description: str,
        topic: str | None,
        keywords: list[str],
        workflow: dict,
    ) -> dict:
        """Save a drafted workflow, switched off. It must say when it runs:
        a workflow with no keywords would take every customer message."""
        keywords = _keywords(keywords)
        if not keywords:
            raise HTTPException(status_code=422, detail="Add at least one keyword so the workflow knows which messages to answer.")
        if topic is not None and topic not in NEW_WORKFLOW_TOPICS:
            raise HTTPException(status_code=422, detail="Unknown topic.")
        errors = _validate(workflow, _catalog())
        if errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})

        subscription = CustomerServiceEventSubscription(
            user_id=workspace_id,
            name=name.strip()[:120] or "New workflow",
            event_type="customer.chat.message.created",
            channel="website",
            workflow_json=workflow,
            filters={"keywords": keywords, **({"intent": topic} if topic else {})},
            is_active=False,
            meta={"source": "studio_prompt", "description": description.strip()[:500], "dispatch_mode": "standard"},
        )
        self.db.add(subscription)
        await self.db.commit()
        return {"workflow_id": str(subscription.id)}

    async def set_workflow_enabled(self, *, workspace_id: UUID, subscription_id: UUID, enabled: bool) -> dict:
        subscription = await self._prompt_workflow(workspace_id, subscription_id)
        subscription.is_active = enabled
        await self.db.commit()
        return {"workflow_id": str(subscription.id), "enabled": enabled}

    async def _prompt_workflow(self, workspace_id: UUID, subscription_id: UUID):
        subscription, _ = await self.studio._subscription(workspace_id, subscription_id)
        if (subscription.meta or {}).get("source") != "studio_prompt":
            raise HTTPException(status_code=409, detail="This workflow can't be changed here.")
        return subscription

    async def set_workflow_keywords(self, *, workspace_id: UUID, subscription_id: UUID, keywords: list[str]) -> dict:
        subscription = await self._prompt_workflow(workspace_id, subscription_id)
        keywords = _keywords(keywords)
        if not keywords:
            raise HTTPException(status_code=422, detail="Add at least one keyword so the workflow knows which messages to answer.")
        subscription.filters = {**(subscription.filters or {}), "keywords": keywords}
        await self.db.commit()
        return {"workflow_id": str(subscription.id), "keywords": keywords}

    async def delete_workflow(self, *, workspace_id: UUID, subscription_id: UUID) -> None:
        subscription = await self._prompt_workflow(workspace_id, subscription_id)
        if subscription.is_active:
            raise HTTPException(status_code=409, detail="Turn this workflow off before deleting it.")
        await self.db.delete(subscription)
        await self.db.commit()
