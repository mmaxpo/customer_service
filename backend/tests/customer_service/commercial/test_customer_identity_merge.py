from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Customer,
    CustomerIdentity,
)
from app.domains.customer_service.services.commercial_operations import (
    CommercialOperationsService,
)
from app.domains.customer_service.services.customer_identity import (
    CustomerIdentityEvidence,
    CustomerIdentityService,
)


@pytest.mark.asyncio
async def test_customer_merge_moves_durable_identities_to_target():
    user_id = uuid4()

    async with SessionLocal() as db:
        identity_service = CustomerIdentityService(db)

        source = await identity_service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="email",
                    value=(f"source-{uuid4().hex}@example.com"),
                    source="merge-test",
                )
            ],
        )

        target = await identity_service.resolve_or_create(
            user_id=user_id,
            workspace_id=None,
            evidence=[
                CustomerIdentityEvidence(
                    identity_type="phone",
                    value="+491701234567",
                    source="merge-test",
                )
            ],
        )

        source_id = source.id
        target_id = target.id

        await db.commit()

        service = CommercialOperationsService(
            db,
            workspace_id=user_id,
        )

        # The identity-transfer behavior under test does not
        # require durable audit fixtures. Existing commercial
        # regression tests cover those separately.
        service._merge_event = lambda *args, **kwargs: None
        service._audit = lambda *args, **kwargs: None

        result = await service.merge_customers(
            source_id,
            target_id,
        )

        assert result["status"] == "merged"

        source_after = await db.scalar(select(Customer).where(Customer.id == source_id))

        assert source_after is not None
        assert source_after.merged_into_id == target_id

        target_identities = list(
            await db.scalars(
                select(CustomerIdentity).where(
                    CustomerIdentity.user_id == user_id,
                    CustomerIdentity.customer_id == target_id,
                )
            )
        )

        identity_types = {row.identity_type for row in target_identities}

        assert "email" in identity_types
        assert "phone" in identity_types

        source_identity_count = len(
            list(
                await db.scalars(
                    select(CustomerIdentity).where(
                        CustomerIdentity.user_id == user_id,
                        CustomerIdentity.customer_id == source_id,
                    )
                )
            )
        )

        assert source_identity_count == 0

        await db.execute(delete(Customer).where(Customer.user_id == user_id))
        await db.commit()
