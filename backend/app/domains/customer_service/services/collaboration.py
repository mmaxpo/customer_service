"""
Working together on conversations: who the teammates are, and telling a
teammate when they are mentioned in an internal note or given a conversation.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.notifications import NotificationService


class CollaborationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def teammates(self, *, workspace_id: UUID) -> list[dict]:
        """Active members of the workspace, for assigning and mentioning."""
        result = await self.db.execute(
            text(
                """
                SELECT u.id, u.full_name, u.email, m.role
                FROM workspace_memberships m
                JOIN "user" u ON u.id = m.user_id
                WHERE m.workspace_id = :workspace_id AND m.status = 'active'
                ORDER BY lower(coalesce(u.full_name, u.email))
                """
            ),
            {"workspace_id": workspace_id},
        )
        return [
            {
                "user_id": str(row.id),
                # The name people type after "@": the full name, or the part
                # of the email before the "@" when no name is set.
                "name": (row.full_name or "").strip() or row.email.split("@")[0],
                "email": row.email,
                "role": row.role,
            }
            for row in result
        ]

    async def notify_mentions(
        self, *, workspace_id: UUID, actor_id: UUID, conversation_id: UUID, body: str
    ) -> list[str]:
        """Notify every teammate written as @Name in an internal note."""
        lowered = body.lower()
        mentioned = []
        team = await self.teammates(workspace_id=workspace_id)
        author = next((m["name"] for m in team if m["user_id"] == str(actor_id)), "A teammate")
        for member in team:
            if member["user_id"] == str(actor_id) or f"@{member['name'].lower()}" not in lowered:
                continue
            await NotificationService(self.db).create(
                workspace_id=workspace_id,
                recipient_user_id=UUID(member["user_id"]),
                kind="mention",
                entity_type="conversation",
                entity_id=conversation_id,
                payload={"from": author, "excerpt": body.strip()[:200]},
            )
            mentioned.append(member["user_id"])
        return mentioned

    async def notify_assignment(
        self, *, workspace_id: UUID, actor_id: UUID, conversation_id: UUID, assignee: str | None
    ) -> None:
        """Tell a teammate that someone else gave them a conversation."""
        if not assignee or assignee == str(actor_id):
            return
        team = await self.teammates(workspace_id=workspace_id)
        if assignee not in {m["user_id"] for m in team}:
            return
        author = next((m["name"] for m in team if m["user_id"] == str(actor_id)), "A teammate")
        await NotificationService(self.db).create(
            workspace_id=workspace_id,
            recipient_user_id=UUID(assignee),
            kind="assigned",
            entity_type="conversation",
            entity_id=conversation_id,
            payload={"from": author},
        )
