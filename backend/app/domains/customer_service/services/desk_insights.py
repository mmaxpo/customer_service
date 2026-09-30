"""
Desk: how well automation and support are doing over a period, compared with
the period before. Counts come from the same job-based log as Live, so the two
screens always agree.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.live_monitor import LiveMonitorService


def _automation(rows: list[dict]) -> dict:
    total = len(rows)
    counts = {key: sum(1 for r in rows if r["outcome"] == key) for key in ("answered", "handed_over", "failed")}
    return {
        "total": total,
        **counts,
        "answered_rate": round(100 * counts["answered"] / total) if total else None,
        "handed_over_rate": round(100 * counts["handed_over"] / total) if total else None,
        "failed_rate": round(100 * counts["failed"] / total) if total else None,
    }


class DeskInsightsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def insights(self, *, workspace_id: UUID, days: int) -> dict:
        now = datetime.now(timezone.utc)
        start, previous_start = now - timedelta(days=days), now - timedelta(days=2 * days)

        rows = await LiveMonitorService(self.db).activity(
            workspace_id=workspace_id, days=2 * days, limit=10_000
        )
        current = [r for r in rows if r["created_at"] >= start]
        previous = [r for r in rows if r["created_at"] < start]

        return {
            "days": days,
            "automation": _automation(current),
            "automation_previous": _automation(previous),
            "rating": await self._rating(workspace_id, start, now),
            "rating_previous": await self._rating(workspace_id, previous_start, start),
            "answer_feedback": await self._answer_feedback(workspace_id, start),
            "top_topics": await self._top_topics(workspace_id, start),
            "lowest_rated": await self._lowest_rated(workspace_id, start),
        }

    async def _rating(self, workspace_id: UUID, start: datetime, end: datetime) -> dict:
        result = await self.db.execute(
            text(
                """
                SELECT score, count(*) FROM cs_csat_surveys
                WHERE workspace_id = :workspace_id AND status = 'answered'
                  AND answered_at >= :start AND answered_at < :end
                GROUP BY score
                """
            ),
            {"workspace_id": workspace_id, "start": start, "end": end},
        )
        distribution = {score: 0 for score in range(1, 6)}
        for score, count in result:
            distribution[score] = count
        responses = sum(distribution.values())
        average = sum(s * c for s, c in distribution.items()) / responses if responses else None
        return {
            "responses": responses,
            "average": round(average, 1) if average is not None else None,
            "distribution": distribution,
        }

    async def _answer_feedback(self, workspace_id: UUID, start: datetime) -> dict:
        result = await self.db.execute(
            text(
                """
                SELECT m.meta->>'customer_feedback' AS feedback, count(*)
                FROM cs_chat_messages m
                JOIN cs_chat_sessions s ON s.id = m.session_id
                WHERE s.user_id = :workspace_id AND m.created_at >= :start
                  AND m.meta ? 'customer_feedback'
                GROUP BY 1
                """
            ),
            {"workspace_id": workspace_id, "start": start},
        )
        counts = dict(result.all())
        return {"helpful": counts.get("helpful", 0), "not_helpful": counts.get("not_helpful", 0)}

    async def _top_topics(self, workspace_id: UUID, start: datetime) -> list[dict]:
        # Latest topic of each conversation the customer wrote in during the period.
        result = await self.db.execute(
            text(
                """
                SELECT topic, count(*) AS conversations FROM (
                  SELECT DISTINCT ON (i.conversation_id) i.intent AS topic
                  FROM cs_conversation_insights i
                  WHERE i.user_id = :workspace_id
                    AND EXISTS (
                      SELECT 1 FROM cs_conversation_messages m
                      WHERE m.conversation_id = i.conversation_id
                        AND m.sender_type = 'customer' AND m.created_at >= :start
                    )
                  ORDER BY i.conversation_id, i.created_at DESC
                ) latest
                GROUP BY topic
                ORDER BY conversations DESC
                LIMIT 8
                """
            ),
            {"workspace_id": workspace_id, "start": start},
        )
        return [{"topic": topic, "conversations": count} for topic, count in result]

    async def _lowest_rated(self, workspace_id: UUID, start: datetime) -> list[dict]:
        result = await self.db.execute(
            text(
                """
                SELECT s.conversation_id, s.score, s.comment, s.answered_at, cust.name AS customer_name
                FROM cs_csat_surveys s
                JOIN cs_conversations c ON c.id = s.conversation_id
                JOIN cs_customers cust ON cust.id = c.customer_id
                WHERE s.workspace_id = :workspace_id AND s.status = 'answered'
                  AND s.answered_at >= :start AND s.score <= 3
                ORDER BY s.score, s.answered_at DESC
                LIMIT 10
                """
            ),
            {"workspace_id": workspace_id, "start": start},
        )
        return [
            {
                "conversation_id": str(row.conversation_id),
                "score": row.score,
                "comment": row.comment,
                "answered_at": row.answered_at,
                "customer_name": row.customer_name,
            }
            for row in result
        ]
