from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import CapabilityMetadata


class CapabilityMetadataRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self,
        *,
        capability_id: str,
        tenant_id: UUID | None = None,
    ) -> CapabilityMetadata | None:
        result = await self.db.execute(
            select(CapabilityMetadata).where(
                CapabilityMetadata.capability_id == capability_id,
                CapabilityMetadata.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(
        self,
        *,
        tenant_id: UUID | None = None,
    ) -> list[CapabilityMetadata]:
        result = await self.db.execute(
            select(CapabilityMetadata).where(CapabilityMetadata.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        *,
        capability_id: str,
        tenant_id: UUID | None = None,
        display_name: str | None = None,
        description: str | None = None,
        domain: str | None = None,
        category: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        extra: dict | None = None,
        is_enabled: bool = True,
    ) -> CapabilityMetadata:
        stmt = insert(CapabilityMetadata).values(
            capability_id=capability_id,
            tenant_id=tenant_id,
            display_name=display_name,
            description=description,
            domain=domain,
            category=category,
            status=status,
            tags=tags or [],
            metadata=extra or {},
            is_enabled=is_enabled,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[
                CapabilityMetadata.capability_id,
                CapabilityMetadata.tenant_id,
            ],
            set_={
                "display_name": display_name,
                "description": description,
                "domain": domain,
                "category": category,
                "status": status,
                "tags": tags or [],
                "metadata": extra or {},
                "is_enabled": is_enabled,
            },
        ).returning(CapabilityMetadata)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one()

    async def delete(
        self,
        *,
        capability_id: str,
        tenant_id: UUID | None = None,
    ) -> bool:
        row = await self.get(capability_id=capability_id, tenant_id=tenant_id)

        if row is None:
            return False

        await self.db.delete(row)
        await self.db.commit()
        return True
