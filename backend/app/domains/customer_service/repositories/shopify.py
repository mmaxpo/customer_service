from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceShopifyConnection,
    CustomerServiceShopifyOrderCache,
)


class ShopifyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def deactivate_active_connections(
        self,
        *,
        user_id,
        shop_domain: str | None = None,
    ) -> None:
        conditions = [
            CustomerServiceShopifyConnection.user_id == user_id,
            CustomerServiceShopifyConnection.status == "active",
        ]

        if shop_domain:
            conditions.append(
                CustomerServiceShopifyConnection.shop_domain == shop_domain
            )

        await self.db.execute(
            update(CustomerServiceShopifyConnection)
            .where(*conditions)
            .values(status="inactive")
        )

    async def list_active_connections(
        self,
        *,
        user_id,
    ):
        result = await self.db.execute(
            select(CustomerServiceShopifyConnection)
            .where(
                CustomerServiceShopifyConnection.user_id == user_id,
                CustomerServiceShopifyConnection.status == "active",
            )
            .order_by(CustomerServiceShopifyConnection.created_at.desc())
        )

        return list(result.scalars().all())

    async def list_connections_for_workspace(self, *, workspace_id):
        """Includes inactive records: an inactive store can still retain a token."""
        result = await self.db.execute(
            select(CustomerServiceShopifyConnection)
            .where(CustomerServiceShopifyConnection.workspace_id == workspace_id)
            .order_by(CustomerServiceShopifyConnection.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_connection(
        self,
        *,
        user_id,
        workspace_id=None,
        shop_domain: str,
        access_token_encrypted: str | None,
        granted_scopes: str | None = None,
    ):
        # Reinstalling a domain updates its durable store record.  It never
        # deactivates sibling stores in the workspace.
        conditions = [CustomerServiceShopifyConnection.shop_domain == shop_domain]
        if workspace_id is not None:
            conditions.append(
                CustomerServiceShopifyConnection.workspace_id == workspace_id
            )
        else:
            conditions.append(CustomerServiceShopifyConnection.user_id == user_id)
            conditions.append(CustomerServiceShopifyConnection.workspace_id.is_(None))
        obj = await self.db.scalar(
            select(CustomerServiceShopifyConnection).where(*conditions)
        )
        if obj is None:
            obj = CustomerServiceShopifyConnection(
                user_id=user_id, workspace_id=workspace_id, shop_domain=shop_domain
            )
            self.db.add(obj)
        obj.access_token_encrypted = access_token_encrypted
        obj.granted_scopes = granted_scopes
        obj.installed_at = datetime.now(timezone.utc)
        obj.revoked_at = None
        obj.reauth_required_at = None
        obj.status = "active"
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_active_connection(self, *, user_id):
        """Legacy helper: only returns a connection when selection is unambiguous."""
        rows = await self.list_active_connections(user_id=user_id)
        return rows[0] if len(rows) == 1 else None

    async def get_connection(self, *, user_id, connection_id):
        result = await self.db.execute(
            select(CustomerServiceShopifyConnection)
            .where(
                CustomerServiceShopifyConnection.user_id == user_id,
                CustomerServiceShopifyConnection.id == connection_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_connection_by_id(self, *, user_id, connection_id):
        result = await self.db.execute(
            select(CustomerServiceShopifyConnection).where(
                CustomerServiceShopifyConnection.user_id == user_id,
                CustomerServiceShopifyConnection.id == connection_id,
                CustomerServiceShopifyConnection.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def get_active_connection_by_shop(self, *, shop_domain: str, user_id=None):
        conditions = [
            CustomerServiceShopifyConnection.shop_domain == shop_domain,
            CustomerServiceShopifyConnection.status == "active",
        ]
        if user_id is not None:
            conditions.append(CustomerServiceShopifyConnection.user_id == user_id)
        result = await self.db.execute(
            select(CustomerServiceShopifyConnection)
            .where(*conditions)
            .order_by(CustomerServiceShopifyConnection.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_store_settings(
        self, *, user_id, connection_id, business_hours_override, timezone_override
    ):
        connection = await self.get_connection(
            user_id=user_id, connection_id=connection_id
        )
        if connection is None:
            return None
        connection.business_hours_override = business_hours_override
        connection.timezone_override = timezone_override
        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def mark_reauth_required(self, *, user_id, connection_id=None) -> None:
        conditions = [
            CustomerServiceShopifyConnection.user_id == user_id,
            CustomerServiceShopifyConnection.status == "active",
        ]
        if connection_id is not None:
            conditions.append(CustomerServiceShopifyConnection.id == connection_id)
        await self.db.execute(
            update(CustomerServiceShopifyConnection)
            .where(*conditions)
            .values(reauth_required_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def deactivate_connection(self, *, user_id, connection_id):
        result = await self.db.execute(
            select(CustomerServiceShopifyConnection)
            .where(
                CustomerServiceShopifyConnection.user_id == user_id,
                CustomerServiceShopifyConnection.id == connection_id,
            )
            .limit(1)
        )
        connection = result.scalar_one_or_none()

        if connection is None:
            return None

        connection.status = "inactive"
        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def cache_order(
        self,
        *,
        user_id,
        shop_domain: str,
        order_id: str,
        order_name: str | None,
        customer_email: str | None,
        payload: dict,
    ):
        obj = CustomerServiceShopifyOrderCache(
            user_id=user_id,
            shop_domain=shop_domain,
            order_id=order_id,
            order_name=order_name,
            customer_email=customer_email,
            payload=payload,
        )

        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def find_cached_order(
        self, *, user_id, order_ref: str, shop_domain: str | None = None
    ):
        normalized = str(order_ref or "").strip()
        without_hash = normalized.lstrip("#")
        with_hash = normalized if normalized.startswith("#") else f"#{normalized}"

        candidates = {
            normalized,
            without_hash,
            with_hash,
        }

        result = await self.db.execute(
            select(CustomerServiceShopifyOrderCache)
            .where(
                CustomerServiceShopifyOrderCache.user_id == user_id,
                *(
                    [CustomerServiceShopifyOrderCache.shop_domain == shop_domain]
                    if shop_domain
                    else []
                ),
                (
                    CustomerServiceShopifyOrderCache.order_id.in_(candidates)
                    | CustomerServiceShopifyOrderCache.order_name.in_(candidates)
                ),
            )
            .order_by(CustomerServiceShopifyOrderCache.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
