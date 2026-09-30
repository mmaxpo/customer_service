from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerIdentity


class CustomerIdentityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find(
        self,
        *,
        user_id: UUID,
        identity_type: str,
        namespace: str,
        normalized_value: str,
    ) -> CustomerIdentity | None:
        return await self.db.scalar(
            select(CustomerIdentity).where(
                CustomerIdentity.user_id == user_id,
                CustomerIdentity.identity_type == identity_type,
                CustomerIdentity.namespace == namespace,
                CustomerIdentity.normalized_value == normalized_value,
            )
        )

    async def list_for_customer(
        self,
        *,
        user_id: UUID,
        customer_id: UUID,
    ) -> list[CustomerIdentity]:
        return list(
            await self.db.scalars(
                select(CustomerIdentity)
                .where(
                    CustomerIdentity.user_id == user_id,
                    CustomerIdentity.customer_id == customer_id,
                )
                .order_by(
                    CustomerIdentity.created_at,
                    CustomerIdentity.id,
                )
            )
        )

    async def create_if_absent(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None,
        customer_id: UUID,
        identity_type: str,
        namespace: str,
        value: str,
        normalized_value: str,
        provider: str | None,
        external_account_id: str | None,
        verified: bool,
        source: str | None,
    ) -> CustomerIdentity:
        statement = (
            pg_insert(CustomerIdentity)
            .values(
                user_id=user_id,
                workspace_id=workspace_id,
                customer_id=customer_id,
                identity_type=identity_type,
                namespace=namespace,
                value=value,
                normalized_value=normalized_value,
                provider=provider,
                external_account_id=external_account_id,
                verified=verified,
                source=source,
            )
            .on_conflict_do_nothing(constraint="uq_cs_customer_identity_scope")
            .returning(CustomerIdentity)
        )

        result = await self.db.execute(statement)
        created = result.scalar_one_or_none()

        if created is not None:
            return created

        existing = await self.find(
            user_id=user_id,
            identity_type=identity_type,
            namespace=namespace,
            normalized_value=normalized_value,
        )

        if existing is None:
            raise RuntimeError("Customer identity conflict could not be recovered")

        return existing
