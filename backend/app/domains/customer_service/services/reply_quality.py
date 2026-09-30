from __future__ import annotations

from app.domains.customer_service.repositories.reply_quality import (
    ReplyQualityRepository,
)


class ReplyQualityService:
    def __init__(self, db):
        self.repo = ReplyQualityRepository(db)

    async def record_review(
        self,
        *,
        user_id,
        conversation_id,
        outcome: str,
        reply_message_id=None,
        score: float | None = None,
        accuracy_score: float | None = None,
        relevance_score: float | None = None,
        tone_score: float | None = None,
        draft_body: str | None = None,
        final_body: str | None = None,
        reviewer_id=None,
        metadata: dict | None = None,
    ):
        scores_payload = {
            "accuracy": accuracy_score,
            "relevance": relevance_score,
            "tone": tone_score,
        }

        if metadata:
            scores_payload["metadata"] = metadata

        return await self.repo.create(
            user_id=user_id,
            conversation_id=conversation_id,
            reply_message_id=reply_message_id,
            review_type="ai_reply",
            outcome=outcome,
            overall_score=score if score is not None else self._default_score(outcome),
            scores=scores_payload,
            accuracy_score=accuracy_score,
            relevance_score=relevance_score,
            tone_score=tone_score,
            draft_body=draft_body,
            final_body=final_body,
            edit_distance=self._edit_distance(draft_body or "", final_body or ""),
            reviewer_id=reviewer_id,
            reviewer_type="agent",
            issues=[],
            recommendations=[],
        )

    async def record_accept_without_edit(
        self,
        *,
        user_id,
        conversation_id,
        reply_message_id=None,
        draft_body: str | None = None,
        final_body: str | None = None,
        reviewer_id=None,
        metadata: dict | None = None,
    ):
        return await self.record_review(
            user_id=user_id,
            conversation_id=conversation_id,
            reply_message_id=reply_message_id,
            outcome="accepted_without_edit",
            score=5.0,
            accuracy_score=5.0,
            relevance_score=5.0,
            tone_score=5.0,
            draft_body=draft_body,
            final_body=final_body or draft_body,
            reviewer_id=reviewer_id,
            metadata=metadata,
        )

    async def record_accept_with_edit(
        self,
        *,
        user_id,
        conversation_id,
        reply_message_id=None,
        draft_body: str | None = None,
        final_body: str | None = None,
        reviewer_id=None,
        metadata: dict | None = None,
    ):
        return await self.record_review(
            user_id=user_id,
            conversation_id=conversation_id,
            reply_message_id=reply_message_id,
            outcome="accepted_with_edit",
            score=4.0,
            accuracy_score=4.0,
            relevance_score=4.0,
            tone_score=4.0,
            draft_body=draft_body,
            final_body=final_body,
            reviewer_id=reviewer_id,
            metadata=metadata,
        )

    async def record_rejection(
        self,
        *,
        user_id,
        conversation_id,
        draft_body: str | None = None,
        reviewer_id=None,
        metadata: dict | None = None,
    ):
        return await self.record_review(
            user_id=user_id,
            conversation_id=conversation_id,
            outcome="rejected",
            score=1.0,
            accuracy_score=1.0,
            relevance_score=1.0,
            tone_score=1.0,
            draft_body=draft_body,
            final_body=None,
            reviewer_id=reviewer_id,
            metadata=metadata,
        )

    async def list_for_conversation(self, *, user_id, conversation_id):
        return await self.repo.list_for_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

    async def analytics(self, *, user_id):
        return await self.repo.aggregate_metrics(user_id=user_id)

    def _default_score(self, outcome: str) -> float:
        if outcome == "accepted_without_edit":
            return 5.0
        if outcome == "accepted_with_edit":
            return 4.0
        if outcome == "rejected":
            return 1.0
        return 3.0

    def _edit_distance(self, left: str, right: str) -> int:
        if left == right:
            return 0

        if not left:
            return len(right)

        if not right:
            return len(left)

        previous = list(range(len(right) + 1))

        for i, left_char in enumerate(left, start=1):
            current = [i]

            for j, right_char in enumerate(right, start=1):
                insert_cost = current[j - 1] + 1
                delete_cost = previous[j] + 1
                replace_cost = previous[j - 1] + (left_char != right_char)

                current.append(min(insert_cost, delete_cost, replace_cost))

            previous = current

        return previous[-1]
