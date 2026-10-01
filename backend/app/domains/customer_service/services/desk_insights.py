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


FIRST_REPLY_BUCKETS = [
    ("Under 1 minute", 60),
    ("1–5 minutes", 300),
    ("5–60 minutes", 3600),
    ("1–24 hours", 86400),
    ("More than 1 day", None),
]
RESOLUTION_BUCKETS = [
    ("Under 1 hour", 3600),
    ("1–8 hours", 28800),
    ("8–24 hours", 86400),
    ("1–7 days", 604800),
    ("More than 7 days", None),
]
BACKLOG_BUCKETS = [
    ("Less than 1 hour", 3600),
    ("1–8 hours", 28800),
    ("8–24 hours", 86400),
    ("1–7 days", 604800),
    ("More than 7 days", None),
]


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[middle], 1)
    return round((ordered[middle - 1] + ordered[middle]) / 2, 1)


def _buckets(values: list[float], buckets: list[tuple[str, int | None]]) -> list[dict]:
    rows, lower = [], 0
    for label, upper in buckets:
        rows.append({"label": label, "value": sum(1 for v in values if v >= lower and (upper is None or v < upper))})
        lower = upper
    return rows


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
            "speed": await self._speed(workspace_id, start, now),
            "speed_previous": await self._speed(workspace_id, previous_start, start),
            "tickets": await self._tickets(workspace_id, start),
        }

    async def _tickets(self, workspace_id: UUID, start: datetime) -> dict:
        # Open and pending are the queue right now; new and resolved are for the period.
        result = await self.db.execute(
            text(
                """
                SELECT lower(t.status::text) AS status, c.channel, t.created_at, t.resolved_at,
                       extract(epoch FROM now() - t.created_at) AS age
                FROM cs_tickets t
                JOIN cs_conversations c ON c.id = t.conversation_id
                WHERE t.user_id = :workspace_id
                """
            ),
            {"workspace_id": workspace_id},
        )
        rows = result.all()
        waiting = [float(row.age) for row in rows if row.status in ("open", "pending")]
        created = [row for row in rows if row.created_at >= start]
        channels: dict[str, int] = {}
        for row in created:
            channels[row.channel] = channels.get(row.channel, 0) + 1
        return {
            "created": len(created),
            "open": sum(1 for row in rows if row.status == "open"),
            "pending": sum(1 for row in rows if row.status == "pending"),
            "resolved": sum(1 for row in rows if row.resolved_at and row.resolved_at >= start),
            "oldest_open_seconds": max(waiting) if waiting else None,
            "backlog": _buckets(waiting, BACKLOG_BUCKETS),
            "by_channel": [
                {"label": channel, "value": count}
                for channel, count in sorted(channels.items(), key=lambda item: -item[1])
            ],
        }

    async def _speed(self, workspace_id: UUID, start: datetime, end: datetime) -> dict:
        # First reply: from the customer's first message to the first answer by
        # the bot or a team member. Conversations are counted in the period
        # their first customer message falls in.
        result = await self.db.execute(
            text(
                """
                SELECT extract(epoch FROM (
                  SELECT min(r.created_at) FROM cs_conversation_messages r
                  WHERE r.conversation_id = first.conversation_id
                    AND lower(r.sender_type::text) IN ('ai', 'agent')
                    AND r.created_at > first.asked_at
                ) - first.asked_at) AS seconds
                FROM (
                  SELECT t.conversation_id, min(m.created_at) AS asked_at
                  FROM cs_tickets t
                  JOIN cs_conversation_messages m ON m.conversation_id = t.conversation_id
                  WHERE t.user_id = :workspace_id AND lower(m.sender_type::text) = 'customer'
                  GROUP BY t.conversation_id
                ) first
                WHERE first.asked_at >= :start AND first.asked_at < :end
                """
            ),
            {"workspace_id": workspace_id, "start": start, "end": end},
        )
        seconds = [row.seconds for row in result]
        replied = [float(value) for value in seconds if value is not None]

        result = await self.db.execute(
            text(
                """
                SELECT extract(epoch FROM resolved_at - created_at) AS seconds
                FROM cs_tickets
                WHERE user_id = :workspace_id AND resolved_at >= :start AND resolved_at < :end
                """
            ),
            {"workspace_id": workspace_id, "start": start, "end": end},
        )
        resolved = [float(row.seconds) for row in result]

        return {
            "first_reply": {
                "conversations": len(seconds),
                "replied": len(replied),
                "median_seconds": _median(replied),
                "buckets": _buckets(replied, FIRST_REPLY_BUCKETS)
                + [{"label": "No reply yet", "value": len(seconds) - len(replied)}],
            },
            "resolution": {
                "resolved": len(resolved),
                "median_seconds": _median(resolved),
                "buckets": _buckets(resolved, RESOLUTION_BUCKETS),
            },
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
