from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    AgentAssistSuggestion,
    AgentAssistSuggestionRevision,
    AgentAssistSuggestionStatus,
    ConversationMessage,
    MessageSenderType,
)


class AgentAssistSuggestionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        conversation_id,
        suggestion: str,
        workflow_run_id=None,
        intent=None,
        confidence=None,
        source_message_id=None,
        meta: dict | None = None,
    ):
        obj = AgentAssistSuggestion(
            conversation_id=conversation_id,
            source_message_id=source_message_id,
            workflow_run_id=workflow_run_id,
            intent=intent,
            confidence=confidence,
            original_suggestion=suggestion,
            current_suggestion=suggestion,
            status=AgentAssistSuggestionStatus.GENERATED,
            meta=meta,
        )

        self.db.add(obj)
        await self.db.flush()

        self.db.add(
            AgentAssistSuggestionRevision(
                suggestion_id=obj.id,
                revision_number=1,
                body=suggestion,
                edited_by=None,
                change_reason="generated",
                meta={"source": "agent_assist"},
            )
        )
        self.db.add(
            self._system_message(
                conversation_id=conversation_id,
                body="Agent Assist generated a reply suggestion.",
                meta={
                    "event": "agent_assist.suggestion_generated",
                    "suggestion_id": str(obj.id),
                    "workflow_run_id": str(workflow_run_id)
                    if workflow_run_id
                    else None,
                },
            )
        )

        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get(self, suggestion_id):
        return await self.db.get(AgentAssistSuggestion, suggestion_id)

    def _system_message(self, *, conversation_id, body: str, meta: dict | None = None):
        return ConversationMessage(
            conversation_id=conversation_id,
            sender_type=MessageSenderType.SYSTEM,
            body=body,
            meta=meta or {},
        )

    async def list_revisions(self, suggestion_id):
        result = await self.db.execute(
            select(AgentAssistSuggestionRevision)
            .where(AgentAssistSuggestionRevision.suggestion_id == suggestion_id)
            .order_by(AgentAssistSuggestionRevision.revision_number.asc())
        )
        return result.scalars().all()

    async def next_revision_number(self, suggestion_id):
        result = await self.db.execute(
            select(func.max(AgentAssistSuggestionRevision.revision_number)).where(
                AgentAssistSuggestionRevision.suggestion_id == suggestion_id
            )
        )
        return (result.scalar_one_or_none() or 0) + 1

    async def update_text(
        self,
        *,
        suggestion_id,
        current_suggestion: str,
        reviewed_by,
        change_reason: str | None = "edited",
    ):
        suggestion = await self.get(suggestion_id)

        if suggestion is None:
            return None

        suggestion.current_suggestion = current_suggestion
        suggestion.status = AgentAssistSuggestionStatus.EDITED
        suggestion.reviewed_by = reviewed_by

        revision_number = await self.next_revision_number(suggestion.id)

        self.db.add(
            AgentAssistSuggestionRevision(
                suggestion_id=suggestion.id,
                revision_number=revision_number,
                body=current_suggestion,
                edited_by=reviewed_by,
                change_reason=change_reason,
                meta={"source": "agent_edit"},
            )
        )

        self.db.add(
            self._system_message(
                conversation_id=suggestion.conversation_id,
                body="Agent edited an Agent Assist suggestion.",
                meta={
                    "event": "agent_assist.suggestion_edited",
                    "suggestion_id": str(suggestion.id),
                    "revision_number": revision_number,
                },
            )
        )

        await self.db.commit()
        await self.db.refresh(suggestion)
        return suggestion

    async def approve(self, *, suggestion_id, approved_by):
        suggestion = await self.get(suggestion_id)

        if suggestion is None:
            return None

        suggestion.status = AgentAssistSuggestionStatus.APPROVED
        suggestion.approved_by = approved_by
        suggestion.reviewed_by = approved_by
        self.db.add(
            self._system_message(
                conversation_id=suggestion.conversation_id,
                body="Agent approved an Agent Assist suggestion.",
                meta={
                    "event": "agent_assist.suggestion_approved",
                    "suggestion_id": str(suggestion.id),
                },
            )
        )
        await self.db.commit()
        await self.db.refresh(suggestion)
        return suggestion

    async def reject(self, *, suggestion_id, reviewed_by):
        suggestion = await self.get(suggestion_id)

        if suggestion is None:
            return None

        suggestion.status = AgentAssistSuggestionStatus.REJECTED
        suggestion.reviewed_by = reviewed_by
        self.db.add(
            self._system_message(
                conversation_id=suggestion.conversation_id,
                body="Agent rejected an Agent Assist suggestion.",
                meta={
                    "event": "agent_assist.suggestion_rejected",
                    "suggestion_id": str(suggestion.id),
                },
            )
        )
        await self.db.commit()
        await self.db.refresh(suggestion)
        return suggestion

    async def send(self, *, suggestion_id, sent_by):
        suggestion = await self.get(suggestion_id)

        if suggestion is None:
            return None

        message = ConversationMessage(
            conversation_id=suggestion.conversation_id,
            sender_type=MessageSenderType.AGENT,
            body=suggestion.current_suggestion,
            meta={
                "source": "agent_assist",
                "suggestion_id": str(suggestion.id),
                "workflow_run_id": str(suggestion.workflow_run_id)
                if suggestion.workflow_run_id
                else None,
            },
        )

        self.db.add(message)
        await self.db.flush()

        self.db.add(
            self._system_message(
                conversation_id=suggestion.conversation_id,
                body="Agent sent an Agent Assist suggestion.",
                meta={
                    "event": "agent_assist.suggestion_sent",
                    "suggestion_id": str(suggestion.id),
                    "sent_message_id": str(message.id),
                },
            )
        )

        suggestion.status = AgentAssistSuggestionStatus.SENT
        suggestion.reviewed_by = sent_by
        suggestion.sent_message_id = message.id

        await self.db.commit()
        await self.db.refresh(suggestion)
        return suggestion

    async def list_for_conversation(self, conversation_id):
        result = await self.db.execute(
            select(AgentAssistSuggestion)
            .where(AgentAssistSuggestion.conversation_id == conversation_id)
            .order_by(AgentAssistSuggestion.created_at.desc())
        )
        return result.scalars().all()
