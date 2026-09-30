from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.customer_service.models import WorkspaceSubscription
from app.domains.customer_service.services.billing_plans import plan_entitlements
from app.tenancy.models import Workspace


ALLOWED_PLANS = {"trial", "starter", "growth", "pro"}
ALLOWED_STATUSES = {"trialing", "active", "past_due", "canceled", "paused"}


class BillingWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply(
        self,
        *,
        raw_body: bytes,
        timestamp: str,
        signature: str,
    ) -> dict:
        secret = settings.BILLING_WEBHOOK_SECRET
        if not secret:
            raise HTTPException(
                status_code=503, detail="Billing webhooks are not configured"
            )
        try:
            parsed_timestamp = int(timestamp)
        except ValueError as exc:
            raise HTTPException(
                status_code=401, detail="Invalid billing webhook"
            ) from exc
        if abs(int(time.time()) - parsed_timestamp) > 300:
            raise HTTPException(status_code=401, detail="Expired billing webhook")
        expected = hmac.new(
            secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid billing webhook")
        try:
            event = json.loads(raw_body)
            event_id = str(event["id"])
            data = event["data"]
            workspace_id = uuid.UUID(str(data["workspace_id"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=422, detail="Malformed billing event"
            ) from exc
        if await self.db.get(Workspace, workspace_id) is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        row = await self.db.get(WorkspaceSubscription, workspace_id)
        if row is None:
            row = WorkspaceSubscription(workspace_id=workspace_id)
            self.db.add(row)
        processed = list((row.entitlements or {}).get("_billing_events") or [])
        if event_id in processed:
            return {"status": "duplicate", "event_id": event_id}
        plan = str(data.get("plan", row.plan))
        subscription_status = str(data.get("status", row.status))
        if plan not in ALLOWED_PLANS or subscription_status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=422, detail="Unsupported billing state")
        # Entitlements are server-owned. Even a valid external event can only
        # select a known plan; it cannot supply arbitrary feature grants.
        entitlements = plan_entitlements(plan)
        entitlements["_billing_events"] = (processed + [event_id])[-20:]
        row.plan = plan
        row.status = subscription_status
        row.provider = str(data.get("provider") or row.provider or "external")
        row.provider_customer_id = (
            data.get("provider_customer_id") or row.provider_customer_id
        )
        row.provider_subscription_id = (
            data.get("provider_subscription_id") or row.provider_subscription_id
        )
        row.entitlements = entitlements
        row.cancel_at_period_end = bool(data.get("cancel_at_period_end", False))
        for field in ("trial_ends_at", "current_period_ends_at"):
            value = data.get(field)
            if value:
                setattr(
                    row,
                    field,
                    datetime.fromisoformat(str(value).replace("Z", "+00:00")),
                )
        await self.db.commit()
        return {
            "status": "applied",
            "event_id": event_id,
            "workspace_id": str(workspace_id),
        }
