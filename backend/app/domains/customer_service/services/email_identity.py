from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import resend
from fastapi import HTTPException
from sqlalchemy import select

from app.domains.customer_service.models import CustomerServiceEmailIdentity


class CustomerServiceEmailIdentityService:
    def __init__(self, db):
        self.db = db

    async def get(self, *, workspace_id):
        return await self.db.scalar(
            select(CustomerServiceEmailIdentity).where(
                CustomerServiceEmailIdentity.workspace_id == workspace_id
            )
        )

    async def configure(self, *, workspace_id, payload):
        identity = await self.get(workspace_id=workspace_id)
        changed = identity is None or any(
            getattr(identity, field) != getattr(payload, field)
            for field in ("from_name", "from_email", "reply_to", "provider_domain_id")
        )
        if identity is None:
            identity = CustomerServiceEmailIdentity(workspace_id=workspace_id)
            self.db.add(identity)
        identity.from_name = payload.from_name
        identity.from_email = payload.from_email
        identity.reply_to = payload.reply_to
        identity.provider_domain_id = payload.provider_domain_id
        if changed:
            identity.verification_status = "pending"
            identity.verified_at = None
        await self.db.commit()
        await self.db.refresh(identity)
        return identity

    async def verify(self, *, workspace_id):
        identity = await self.get(workspace_id=workspace_id)
        if identity is None or not identity.provider_domain_id:
            raise HTTPException(
                status_code=422,
                detail="Configure a Resend domain before verification",
            )
        try:
            domain = await asyncio.to_thread(
                resend.Domains.get,
                identity.provider_domain_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=424,
                detail="Could not verify the email domain with Resend",
            ) from exc
        status = (
            domain.get("status")
            if isinstance(domain, dict)
            else getattr(domain, "status", None)
        )
        domain_name = (
            domain.get("name")
            if isinstance(domain, dict)
            else getattr(domain, "name", None)
        )
        sender_domain = identity.from_email.rsplit("@", 1)[-1].lower()
        if status == "verified" and (
            not domain_name or sender_domain != str(domain_name).lower()
        ):
            raise HTTPException(
                status_code=422,
                detail="Sender email must use the verified Resend domain",
            )
        identity.verification_status = (
            "verified" if status == "verified" else str(status or "pending")
        )
        identity.verified_at = (
            datetime.now(timezone.utc) if status == "verified" else None
        )
        await self.db.commit()
        await self.db.refresh(identity)
        return identity
