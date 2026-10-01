"""
Routing: "who gets what". A short list of rules over the real team members:
a topic goes to one person, and everything else goes to one person, to the
least busy person, or stays unassigned. Rules are stored as routing policies
(`meta.source = "assignment_rules"`); a conversation is assigned once, when
its topic is known and its ticket has no assignee yet.
"""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

LEAST_BUSY = "least_busy"
SOURCE = "assignment_rules"


class AssignmentRulesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _members(self, workspace_id: UUID) -> list[str]:
        result = await self.db.execute(
            text(
                "SELECT user_id FROM workspace_memberships "
                "WHERE workspace_id = :workspace_id AND status = 'active'"
            ),
            {"workspace_id": workspace_id},
        )
        return [str(user_id) for (user_id,) in result]

    async def rules(self, *, workspace_id: UUID) -> dict:
        result = await self.db.execute(
            text(
                """
                SELECT intent, strategy, candidate_assignee_ids, is_fallback
                FROM cs_routing_policies
                WHERE user_id = :workspace_id AND is_active AND meta->>'source' = :source
                ORDER BY is_fallback, priority_rank
                """
            ),
            {"workspace_id": workspace_id, "source": SOURCE},
        )
        topics, default = [], None
        for row in result:
            assignee = (row.candidate_assignee_ids or [None])[0] or LEAST_BUSY
            if row.is_fallback:
                default = assignee
            else:
                topics.append({"topic": row.intent, "assignee": assignee})
        return {"topics": topics, "default": default}

    async def save(self, *, workspace_id: UUID, topics: list[dict], default: str | None) -> dict:
        members = set(await self._members(workspace_id))
        for assignee in [*(rule["assignee"] for rule in topics), default]:
            if assignee not in (None, LEAST_BUSY) and assignee not in members:
                raise HTTPException(status_code=422, detail="That person is not an active team member.")
        if len({rule["topic"] for rule in topics}) != len(topics):
            raise HTTPException(status_code=422, detail="Each topic can have only one rule.")

        await self.db.execute(
            text("DELETE FROM cs_routing_policies WHERE user_id = :workspace_id AND meta->>'source' = :source"),
            {"workspace_id": workspace_id, "source": SOURCE},
        )
        rows = [(rule["topic"], rule["assignee"], False) for rule in topics]
        if default is not None:
            rows.append((None, default, True))
        for rank, (topic, assignee, is_fallback) in enumerate(rows):
            await self.db.execute(
                text(
                    """
                    INSERT INTO cs_routing_policies
                      (id, user_id, name, intent, strategy, candidate_assignee_ids,
                       is_active, meta, priority_rank, is_fallback, candidate_team_ids, candidate_queue_ids)
                    VALUES
                      (:id, :workspace_id, :name, :intent, :strategy, CAST(:assignees AS jsonb),
                       true, CAST(:meta AS jsonb), :rank, :is_fallback, '[]'::jsonb, '[]'::jsonb)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "workspace_id": workspace_id,
                    "name": f"Assignment rule: {topic or 'everything else'}",
                    "intent": topic,
                    "strategy": "least_loaded" if assignee == LEAST_BUSY else "direct",
                    "assignees": "[]" if assignee == LEAST_BUSY else f'["{assignee}"]',
                    "meta": f'{{"source": "{SOURCE}"}}',
                    "rank": rank,
                    "is_fallback": is_fallback,
                },
            )
        await self.db.commit()
        return await self.rules(workspace_id=workspace_id)

    async def assign(self, *, workspace_id: UUID, conversation_id: UUID) -> str | None:
        """Assign the conversation's ticket by the rules, if it has no assignee."""
        rules = await self.rules(workspace_id=workspace_id)
        if not rules["topics"] and rules["default"] is None:
            return None

        row = (
            await self.db.execute(
                text(
                    """
                    SELECT t.id,
                           (SELECT i.intent FROM cs_conversation_insights i
                             WHERE i.conversation_id = t.conversation_id
                             ORDER BY i.created_at DESC LIMIT 1) AS topic
                    FROM cs_tickets t
                    WHERE t.conversation_id = :conversation_id AND t.user_id = :workspace_id
                      AND t.assigned_to IS NULL
                    """
                ),
                {"conversation_id": conversation_id, "workspace_id": workspace_id},
            )
        ).first()
        if row is None:
            return None

        assignee = next(
            (rule["assignee"] for rule in rules["topics"] if rule["topic"] == row.topic),
            rules["default"],
        )
        members = await self._members(workspace_id)
        if assignee == LEAST_BUSY:
            result = await self.db.execute(
                text(
                    """
                    SELECT assigned_to, count(*) FROM cs_tickets
                    WHERE user_id = :workspace_id AND assigned_to IS NOT NULL
                      AND status::text NOT IN ('RESOLVED', 'CLOSED')
                    GROUP BY assigned_to
                    """
                ),
                {"workspace_id": workspace_id},
            )
            open_counts = dict(result.all())
            assignee = min(members, key=lambda member: open_counts.get(member, 0), default=None)
        if assignee is None or assignee not in members:
            return None

        await self.db.execute(
            text("UPDATE cs_tickets SET assigned_to = :assignee WHERE id = :id"),
            {"assignee": assignee, "id": row.id},
        )
        await self.db.commit()
        return assignee
