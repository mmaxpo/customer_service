from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceReplySignature


async def resolve_reply_signature(
    db: AsyncSession, *, workspace_id: UUID, actor_user_id: UUID
) -> str | None:
    rows = list(
        await db.scalars(
            select(CustomerServiceReplySignature).where(
                CustomerServiceReplySignature.workspace_id == workspace_id,
                CustomerServiceReplySignature.is_enabled.is_(True),
                CustomerServiceReplySignature.scope_key.in_(
                    [f"user:{actor_user_id}", "merchant"]
                ),
            )
        )
    )
    by_scope = {row.scope_key: row for row in rows}
    selected = by_scope.get(f"user:{actor_user_id}") or by_scope.get("merchant")
    return selected.body if selected else None


__all__ = ["resolve_reply_signature"]
