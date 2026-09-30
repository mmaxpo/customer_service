from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Customer,
    CustomerIdentity,
)
from app.domains.customer_service.services.customer_identity import (
    CustomerIdentityConflictError,
    CustomerIdentityEvidence,
    CustomerIdentityService,
)


@pytest.mark.asyncio
async def test_email_identity_normalizes_and_resolves_same_customer():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = CustomerIdentityService(db)

        first = await service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="email",
                    value=" Buyer@Example.COM ",
                    source="test",
                )
            ],
            email=" Buyer@Example.COM ",
            name="Buyer",
        )

        second = await service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="email",
                    value="buyer@example.com",
                    source="test",
                )
            ],
            email="buyer@example.com",
        )

        await db.commit()

        assert first.id == second.id
        assert second.email == "buyer@example.com"

        count = await db.scalar(
            select(func.count(CustomerIdentity.id)).where(
                CustomerIdentity.user_id == user_id,
                CustomerIdentity.identity_type == "email",
                CustomerIdentity.normalized_value == "buyer@example.com",
            )
        )

        assert count == 1


@pytest.mark.asyncio
async def test_phone_and_provider_identity_resolve_same_customer():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = CustomerIdentityService(db)

        customer = await service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="phone",
                    value="+49 (170) 123-4567",
                    source="whatsapp",
                ),
                CustomerIdentityEvidence(
                    identity_type="provider_customer",
                    namespace="whatsapp:wa-account-1",
                    value="wa-customer-1",
                    provider="whatsapp",
                    external_account_id="wa-account-1",
                    source="whatsapp",
                ),
            ],
            phone="+49 (170) 123-4567",
        )

        await db.commit()

        resolved = await service.resolve_existing(
            user_id=user_id,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="provider_customer",
                    namespace="whatsapp:wa-account-1",
                    value="wa-customer-1",
                )
            ],
        )

        assert resolved is not None
        assert resolved.id == customer.id
        assert customer.phone == "+491701234567"


@pytest.mark.asyncio
async def test_same_external_id_isolated_by_provider_namespace():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = CustomerIdentityService(db)

        whatsapp_customer = await service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="provider_customer",
                    namespace="whatsapp:acct",
                    value="same-id",
                    provider="whatsapp",
                    external_account_id="acct",
                )
            ],
        )

        instagram_customer = await service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="provider_customer",
                    namespace="instagram:acct",
                    value="same-id",
                    provider="instagram",
                    external_account_id="acct",
                )
            ],
        )

        await db.commit()

        assert whatsapp_customer.id != instagram_customer.id


@pytest.mark.asyncio
async def test_conflicting_identity_evidence_does_not_auto_merge():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = CustomerIdentityService(db)

        customer_a = await service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="email",
                    value="a@example.com",
                )
            ],
        )

        customer_b = await service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="phone",
                    value="+491111111111",
                )
            ],
        )

        await db.flush()

        with pytest.raises(CustomerIdentityConflictError):
            await service.resolve_existing(
                user_id=user_id,
                evidence=[
                    CustomerIdentityEvidence(
                        identity_type="email",
                        value="a@example.com",
                    ),
                    CustomerIdentityEvidence(
                        identity_type="phone",
                        value="+491111111111",
                    ),
                ],
            )

        assert customer_a.id != customer_b.id


@pytest.mark.asyncio
async def test_concurrent_same_identity_creates_one_customer():
    user_id = uuid4()
    email = f"race-{uuid4().hex}@example.com"

    async def resolve():
        async with SessionLocal() as db:
            service = CustomerIdentityService(db)

            customer = await service.resolve_or_create(
                user_id=user_id,
                workspace_id=None,
                evidence=[
                    CustomerIdentityEvidence(
                        identity_type="email",
                        value=email,
                    )
                ],
                email=email,
            )

            await db.commit()

            return customer.id

    first, second = await asyncio.gather(
        resolve(),
        resolve(),
    )

    assert first == second

    async with SessionLocal() as db:
        customer_count = await db.scalar(
            select(func.count(Customer.id)).where(
                Customer.user_id == user_id,
                Customer.email == email,
            )
        )

        identity_count = await db.scalar(
            select(func.count(CustomerIdentity.id)).where(
                CustomerIdentity.user_id == user_id,
                CustomerIdentity.identity_type == "email",
                CustomerIdentity.normalized_value == email,
            )
        )

    assert customer_count == 1
    assert identity_count == 1
