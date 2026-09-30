"""
Customer feedback from the chat widget: a thumbs up/down on an answer, and a
1-5 rating for the chat. A thumbs-down on an automated answer flags the run
that sent it, so it shows in the admin's Needs review queue.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models.commercial import CustomerServiceCSATSurvey
from app.domains.customer_service.models.quality import CustomerServiceQualityReview
from app.domains.customer_service.services.automation_studio import RUN_FLAG_REVIEW_TYPE


class CustomerFeedbackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _link(self, workspace_id: UUID, session_id: UUID):
        row = (
            await self.db.execute(
                text(
                    """
                    SELECT conversation_id, ticket_id FROM cs_chat_inbox_links
                    WHERE user_id = :workspace_id AND chat_session_id = :session_id
                    """
                ),
                {"workspace_id": workspace_id, "session_id": session_id},
            )
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return row

    async def answer_feedback(
        self, *, workspace_id: UUID, session_id: UUID, message_id: UUID, helpful: bool
    ) -> dict:
        link = await self._link(workspace_id, session_id)
        message = (
            await self.db.execute(
                text(
                    """
                    SELECT id, role, meta FROM cs_chat_messages
                    WHERE id = :message_id AND session_id = :session_id
                    """
                ),
                {"message_id": message_id, "session_id": session_id},
            )
        ).first()
        if message is None or message.role == "customer":
            raise HTTPException(status_code=404, detail="Answer not found")
        if isinstance(message.meta, dict) and message.meta.get("customer_feedback"):
            return {"status": "already_recorded"}

        feedback = "helpful" if helpful else "not_helpful"
        await self.db.execute(
            text(
                """
                UPDATE cs_chat_messages
                SET meta = (CASE WHEN jsonb_typeof(meta) = 'object' THEN meta ELSE '{}'::jsonb END)
                           || jsonb_build_object('customer_feedback', CAST(:feedback AS text))
                WHERE id = :message_id
                """
            ),
            {"feedback": feedback, "message_id": message_id},
        )

        if not helpful:
            # The reply step records which chat message it sent.
            run_id = (
                await self.db.execute(
                    text(
                        """
                        SELECT e.workflow_run_id FROM workflow_run_events e
                        JOIN workflow_runs r ON r.workflow_run_id = e.workflow_run_id
                        WHERE r.user_id = :workspace_id
                          AND r.thread_id = :conversation_id
                          AND e.event->'output'->>'chat_message_id' = :message_id
                        LIMIT 1
                        """
                    ),
                    {
                        "workspace_id": workspace_id,
                        "conversation_id": link.conversation_id,
                        "message_id": str(message_id),
                    },
                )
            ).scalar()
            if run_id is not None:
                self.db.add(
                    CustomerServiceQualityReview(
                        user_id=workspace_id,
                        conversation_id=link.conversation_id,
                        overall_score=0.0,
                        issues=[
                            {
                                "run_id": str(run_id),
                                "step_id": None,
                                "message_id": str(message_id),
                                "note": "The customer said this answer wasn't helpful.",
                            }
                        ],
                        reviewer_type="customer",
                        reviewer_id=None,
                        review_type=RUN_FLAG_REVIEW_TYPE,
                        outcome="open",
                    )
                )
        await self.db.commit()
        return {"status": "recorded", "feedback": feedback}

    async def rate_chat(
        self, *, workspace_id: UUID, session_id: UUID, score: int, comment: str | None
    ) -> dict:
        link = await self._link(workspace_id, session_id)
        now = datetime.now(timezone.utc)
        survey = await self.db.scalar(
            select(CustomerServiceCSATSurvey).where(
                CustomerServiceCSATSurvey.workspace_id == workspace_id,
                CustomerServiceCSATSurvey.conversation_id == link.conversation_id,
            )
        )
        if survey is None:
            # Chat ratings don't use an emailed link; the token is only a
            # unique placeholder for the existing survey table.
            survey = CustomerServiceCSATSurvey(
                workspace_id=workspace_id,
                conversation_id=link.conversation_id,
                ticket_id=link.ticket_id,
                token_hash=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
                sent_at=now,
            )
            self.db.add(survey)
        survey.score = score
        survey.comment = comment
        survey.status = "answered"
        survey.answered_at = now
        await self.db.commit()
        return {"status": "recorded"}
