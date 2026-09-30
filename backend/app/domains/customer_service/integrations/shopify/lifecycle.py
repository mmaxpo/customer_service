from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceShopifyConnection,
    CustomerServiceShopifyOrderCache,
    ShopifyOAuthInstallSession,
    ShopifyWebhookReceipt,
    WorkspaceSubscription,
)


class InvalidShopifyStateError(Exception):
    """The OAuth state is missing, expired, replayed, or store-mismatched."""


@dataclass(frozen=True)
class ConsumedShopifyInstall:
    user_id: UUID
    workspace_id: UUID
    shop_domain: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def create_install_state(
    db: AsyncSession,
    *,
    user_id: UUID,
    workspace_id: UUID,
    shop_domain: str,
) -> str:
    state = secrets.token_urlsafe(48)
    db.add(
        ShopifyOAuthInstallSession(
            initiated_by_user_id=user_id,
            workspace_id=workspace_id,
            shop_domain=shop_domain,
            state_hash=_hash(state),
            expires_at=_now() + timedelta(minutes=10),
        )
    )
    await db.commit()
    return state


async def consume_install_state(
    db: AsyncSession,
    *,
    state: str,
    shop_domain: str,
) -> ConsumedShopifyInstall:
    result = await db.execute(
        select(ShopifyOAuthInstallSession)
        .where(ShopifyOAuthInstallSession.state_hash == _hash(state))
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    now = _now()
    if (
        row is None
        or row.consumed_at is not None
        or row.expires_at <= now
        or not hmac.compare_digest(row.shop_domain, shop_domain)
    ):
        raise InvalidShopifyStateError
    row.consumed_at = now
    await db.commit()
    return ConsumedShopifyInstall(
        user_id=row.initiated_by_user_id,
        workspace_id=row.workspace_id,
        shop_domain=row.shop_domain,
    )


def verify_webhook_hmac(*, body: bytes, received: str, secret: str) -> bool:
    digest = base64.b64encode(
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("ascii")
    return hmac.compare_digest(digest, received)


async def process_compliance_webhook(
    db: AsyncSession,
    *,
    webhook_id: str,
    shop_domain: str,
    topic: str,
    payload: dict,
) -> str:
    status = "pending_export" if topic == "customers/data_request" else "processed"
    db.add(
        ShopifyWebhookReceipt(
            webhook_id=webhook_id,
            shop_domain=shop_domain,
            topic=topic,
            status=status,
            payload=payload,
        )
    )
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return "duplicate"

    if topic in {"app/uninstalled", "shop/redact"}:
        workspace_ids = select(CustomerServiceShopifyConnection.user_id).where(
            CustomerServiceShopifyConnection.shop_domain == shop_domain
        )
        await db.execute(
            update(WorkspaceSubscription)
            .where(WorkspaceSubscription.workspace_id.in_(workspace_ids))
            .values(
                status="canceled",
                entitlements={},
                cancel_at_period_end=False,
            )
        )
        await db.execute(
            update(CustomerServiceShopifyConnection)
            .where(
                CustomerServiceShopifyConnection.shop_domain == shop_domain,
            )
            .values(
                status="inactive",
                access_token_encrypted=None,
                revoked_at=_now(),
            )
        )
    if topic in {"customers/redact", "shop/redact"}:
        # Conservatively erase the store cache. This avoids retaining customer
        # data when legacy cache payloads cannot be reliably filtered by ID.
        await db.execute(
            delete(CustomerServiceShopifyOrderCache).where(
                CustomerServiceShopifyOrderCache.shop_domain == shop_domain,
            )
        )
    await db.commit()
    return status


async def process_commerce_webhook(
    db: AsyncSession,
    *,
    webhook_id: str,
    shop_domain: str,
    topic: str,
    payload: dict,
) -> str:
    """Apply a Shopify order event to the local cache after receipt dedupe.

    Shopify retries deliveries, so the receipt is the source of truth for
    idempotency. Events without a matching active installation are still
    acknowledged but are not written into another workspace's cache.
    """
    status = await process_compliance_webhook(
        db,
        webhook_id=webhook_id,
        shop_domain=shop_domain,
        topic=topic,
        payload=payload,
    )
    if status == "duplicate":
        return status

    connection = await db.scalar(
        select(CustomerServiceShopifyConnection)
        .where(
            CustomerServiceShopifyConnection.shop_domain == shop_domain,
            CustomerServiceShopifyConnection.status == "active",
        )
        .order_by(CustomerServiceShopifyConnection.created_at.desc())
        .limit(1)
    )
    order_id = payload.get("id") or payload.get("order_id")
    if connection is None or order_id is None:
        return "processed"

    order_id = str(order_id)
    cached = await db.scalar(
        select(CustomerServiceShopifyOrderCache)
        .where(
            CustomerServiceShopifyOrderCache.user_id == connection.user_id,
            CustomerServiceShopifyOrderCache.shop_domain == shop_domain,
            CustomerServiceShopifyOrderCache.order_id == order_id,
        )
        .limit(1)
    )
    if cached is None:
        db.add(
            CustomerServiceShopifyOrderCache(
                user_id=connection.user_id,
                shop_domain=shop_domain,
                order_id=order_id,
                order_name=payload.get("name"),
                customer_email=payload.get("email"),
                payload=payload,
            )
        )
    else:
        cached.order_name = payload.get("name") or cached.order_name
        cached.customer_email = payload.get("email") or cached.customer_email
        cached.payload = payload
    await db.commit()
    return "processed"


__all__ = [
    "ConsumedShopifyInstall",
    "InvalidShopifyStateError",
    "consume_install_state",
    "create_install_state",
    "process_compliance_webhook",
    "process_commerce_webhook",
    "verify_webhook_hmac",
]
