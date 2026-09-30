from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import AgentAssistSuggestionStatus
from app.domains.customer_service.repositories.agent_assist import (
    AgentAssistSuggestionRepository,
)
from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.services.ai_context_policy import (
    CustomerServiceAIContextPolicy,
)
from app.domains.customer_service.workflows.reply_suggestion_workflow import (
    build_reply_suggestion_input,
    build_reply_suggestion_workflow,
)
from app.domains.customer_service.workflows.runtime_bridge import (
    CustomerServiceWorkflowRuntimeBridge,
    extract_workflow_answer,
)


class CustomerServiceAgentAssistService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        user_id,
        request=None,
        run_store=None,
        event_sink=None,
    ):
        self.db = db
        self.user_id = user_id
        self.request = request
        self.run_store = run_store
        self.event_sink = event_sink
        self.conversation_repo = ConversationRepository(db)
        self.suggestion_repo = AgentAssistSuggestionRepository(db)
        self.context_policy = CustomerServiceAIContextPolicy.from_env()

    async def suggest_reply(self, conversation_id):
        conversation = await self.conversation_repo.get_detail(
            user_id=self.user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            return None

        recent_messages = (
            await self.conversation_repo.list_recent_context_messages(
                user_id=self.user_id,
                conversation_id=conversation.id,
                limit=self.context_policy.recent_message_limit,
                include_internal_notes=self.context_policy.include_internal_notes,
            )
            or []
        )

        workflow_meta = (
            await self.conversation_repo.get_latest_workflow_message_meta(
                user_id=self.user_id,
                conversation_id=conversation.id,
                limit=self.context_policy.recent_message_limit,
            )
            or {}
        )

        workflow = build_reply_suggestion_workflow()
        message = build_reply_suggestion_input(
            conversation,
            messages=recent_messages,
            workflow_meta=workflow_meta,
        )

        runtime = CustomerServiceWorkflowRuntimeBridge(
            request=self.request,
            db=self.db,
            user_id=self.user_id,
            run_store=self.run_store,
            event_sink=self.event_sink,
        )

        result = await runtime.run_reply_suggestion(
            thread_id=conversation.id,
            workflow=workflow,
            message=message,
        )

        suggestion_text = extract_workflow_answer(result)
        workflow_run_id = self._workflow_run_id(result)
        intent = self._latest_intent_from_workflow_meta(workflow_meta)
        confidence = self._latest_confidence_from_workflow_meta(workflow_meta)

        suggestion = await self.suggestion_repo.create(
            conversation_id=conversation.id,
            suggestion=suggestion_text,
            workflow_run_id=workflow_run_id,
            intent=intent,
            confidence=confidence,
            meta={
                "source": "workflow_runtime",
                "workflow_run_id": str(workflow_run_id) if workflow_run_id else None,
            },
        )

        return {
            "id": suggestion.id,
            "conversation_id": suggestion.conversation_id,
            "suggestion": suggestion.current_suggestion,
            "source": "workflow_runtime",
            "intent": suggestion.intent,
            "confidence": suggestion.confidence,
            "workflow_run_id": suggestion.workflow_run_id,
            "status": suggestion.status,
            "created_at": suggestion.created_at,
        }

    async def list_conversation_suggestions(self, conversation_id):
        conversation = await self.conversation_repo.get_detail(
            user_id=self.user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return await self.suggestion_repo.list_for_conversation(conversation.id)

    async def edit_suggestion(self, suggestion_id, payload):
        suggestion = await self._get_owned_suggestion(suggestion_id)

        if suggestion.status in {
            AgentAssistSuggestionStatus.SENT,
            AgentAssistSuggestionStatus.REJECTED,
        }:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot edit suggestion with status '{suggestion.status}'.",
            )

        return await self.suggestion_repo.update_text(
            suggestion_id=suggestion.id,
            current_suggestion=payload.current_suggestion,
            reviewed_by=self.user_id,
            change_reason=payload.change_reason or "edited",
        )

    async def approve_suggestion(self, suggestion_id):
        suggestion = await self._get_owned_suggestion(suggestion_id)

        if suggestion.status in {
            AgentAssistSuggestionStatus.SENT,
            AgentAssistSuggestionStatus.REJECTED,
        }:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot approve suggestion with status '{suggestion.status}'.",
            )

        return await self.suggestion_repo.approve(
            suggestion_id=suggestion.id,
            approved_by=self.user_id,
        )

    async def reject_suggestion(self, suggestion_id):
        suggestion = await self._get_owned_suggestion(suggestion_id)

        if suggestion.status == AgentAssistSuggestionStatus.SENT:
            raise HTTPException(
                status_code=409, detail="Cannot reject a sent suggestion."
            )

        return await self.suggestion_repo.reject(
            suggestion_id=suggestion.id,
            reviewed_by=self.user_id,
        )

    async def send_suggestion(self, suggestion_id):
        suggestion = await self._get_owned_suggestion(suggestion_id)

        if suggestion.status == AgentAssistSuggestionStatus.SENT:
            raise HTTPException(status_code=409, detail="Suggestion already sent.")

        if suggestion.status == AgentAssistSuggestionStatus.REJECTED:
            raise HTTPException(
                status_code=409, detail="Cannot send a rejected suggestion."
            )

        return await self.suggestion_repo.send(
            suggestion_id=suggestion.id,
            sent_by=self.user_id,
        )

    async def list_revisions(self, suggestion_id):
        suggestion = await self._get_owned_suggestion(suggestion_id)
        return await self.suggestion_repo.list_revisions(suggestion.id)

    async def _get_owned_suggestion(self, suggestion_id):
        suggestion = await self.suggestion_repo.get(suggestion_id)

        if suggestion is None:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        conversation = await self.conversation_repo.get_detail(
            user_id=self.user_id,
            conversation_id=suggestion.conversation_id,
        )

        if conversation is None:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        return suggestion

    def _latest_intent_from_workflow_meta(self, workflow_meta: dict | None):
        classification = (workflow_meta or {}).get("classification") or {}
        return classification.get("intent") or "general"

    def _latest_confidence_from_workflow_meta(self, workflow_meta: dict | None):
        classification = (workflow_meta or {}).get("classification") or {}
        return classification.get("confidence")

    def _workflow_run_id(self, result: dict):
        if not isinstance(result, dict):
            return None

        meta = result.get("meta") or {}
        state = result.get("state") or {}
        final_state = meta.get("final_state") or {}

        return (
            meta.get("workflow_run_id")
            or result.get("workflow_run_id")
            or result.get("run_id")
            or state.get("workflow_run_id")
            or final_state.get("workflow_run_id")
        )
