from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Conversation,
    Customer,
)
from app.main import app


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-customer-identity@example.com"


async def _cleanup(
    *,
    conversation_ids,
    customer_ids,
):
    async with SessionLocal() as db:
        ticket_ids = list(
            (
                await db.execute(
                    text(
                        """
                        SELECT id
                        FROM cs_tickets
                        WHERE conversation_id =
                            ANY(CAST(:conversation_ids AS uuid[]))
                        """
                    ),
                    {
                        "conversation_ids": conversation_ids,
                    },
                )
            )
            .scalars()
            .all()
        )

        await db.execute(
            text(
                """
                DELETE FROM cs_external_message_links
                WHERE conversation_id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        await db.execute(
            text(
                """
                DELETE FROM cs_external_conversation_links
                WHERE conversation_id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        await db.execute(
            text(
                """
                DELETE FROM cs_agent_assist_suggestions
                WHERE conversation_id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        await db.execute(
            text(
                """
                DELETE FROM cs_conversation_insights
                WHERE conversation_id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        await db.execute(
            text(
                """
                DELETE FROM cs_conversation_tags
                WHERE conversation_id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        await db.execute(
            text(
                """
                DELETE FROM cs_quality_reviews
                WHERE conversation_id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        await db.execute(
            text(
                """
                DELETE FROM cs_suggested_actions
                WHERE conversation_id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        if ticket_ids:
            await db.execute(
                text(
                    """
                    DELETE FROM cs_sla_violations
                    WHERE ticket_id =
                        ANY(CAST(:ticket_ids AS uuid[]))
                    """
                ),
                {
                    "ticket_ids": ticket_ids,
                },
            )

            await db.execute(
                text(
                    """
                    DELETE FROM cs_ticket_assignments
                    WHERE ticket_id =
                        ANY(CAST(:ticket_ids AS uuid[]))
                    """
                ),
                {
                    "ticket_ids": ticket_ids,
                },
            )

            await db.execute(
                text(
                    """
                    DELETE FROM cs_tickets
                    WHERE id =
                        ANY(CAST(:ticket_ids AS uuid[]))
                    """
                ),
                {
                    "ticket_ids": ticket_ids,
                },
            )

        await db.execute(
            text(
                """
                DELETE FROM cs_conversation_messages
                WHERE conversation_id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        await db.execute(
            text(
                """
                DELETE FROM cs_conversations
                WHERE id =
                    ANY(CAST(:conversation_ids AS uuid[]))
                """
            ),
            {
                "conversation_ids": conversation_ids,
            },
        )

        if customer_ids:
            await db.execute(
                text(
                    """
                    DELETE FROM cs_customers
                    WHERE id =
                        ANY(CAST(:customer_ids AS uuid[]))
                    """
                ),
                {
                    "customer_ids": customer_ids,
                },
            )

        await db.commit()


@pytest.mark.asyncio
async def test_concurrent_omnichannel_messages_share_customer_identity():
    user = FakeUser()

    customer_email = f"omni-race-{uuid4().hex}@example.com"

    external_account_id = f"wa-account-{uuid4().hex}"

    conversation_ids = []
    customer_ids = []

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first_payload = {
                "channel": "whatsapp",
                "external_account_id": external_account_id,
                "external_thread_id": f"thread-a-{uuid4()}",
                "external_message_id": f"message-a-{uuid4()}",
                "external_customer_id": f"customer-a-{uuid4()}",
                "customer_name": "Concurrent Omni Buyer",
                "customer_email": customer_email,
                "body": "First concurrent message",
            }

            second_payload = {
                "channel": "whatsapp",
                "external_account_id": external_account_id,
                "external_thread_id": f"thread-b-{uuid4()}",
                "external_message_id": f"message-b-{uuid4()}",
                "external_customer_id": f"customer-b-{uuid4()}",
                "customer_name": "Concurrent Omni Buyer",
                "customer_email": customer_email.upper(),
                "body": "Second concurrent message",
            }

            first, second = await asyncio.gather(
                client.post(
                    "/customer-service/omnichannel/inbound",
                    json=first_payload,
                ),
                client.post(
                    "/customer-service/omnichannel/inbound",
                    json=second_payload,
                ),
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            conversation_ids.extend(
                [
                    first.json()["conversation_id"],
                    second.json()["conversation_id"],
                ]
            )

            async with SessionLocal() as db:
                customers = list(
                    (
                        await db.execute(
                            select(Customer).where(
                                Customer.user_id == user.id,
                                func.lower(Customer.email) == customer_email.lower(),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                customer_ids.extend(customer.id for customer in customers)

                assert len(customers) == 1

                assert customers[0].email == customer_email.lower()

                conversations = list(
                    (
                        await db.execute(
                            select(Conversation).where(
                                Conversation.id.in_(conversation_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                assert len(conversations) == 2

                assert {conversation.customer_id for conversation in conversations} == {
                    customers[0].id
                }

    finally:
        app.dependency_overrides.clear()

        if conversation_ids:
            await _cleanup(
                conversation_ids=conversation_ids,
                customer_ids=customer_ids,
            )


@pytest.mark.asyncio
async def test_phone_only_identity_converges_across_threads():
    user = FakeUser()

    unique_digits = str(10_000_000_000 + uuid4().int % 80_000_000_000)

    phone_a = f"+{unique_digits}"
    phone_b = f"+{unique_digits[:2]} ({unique_digits[2:5]}) {unique_digits[5:]}"

    account_id = f"wa-phone-{uuid4().hex}"

    conversation_ids = []
    customer_ids = []

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": account_id,
                    "external_thread_id": (f"phone-thread-a-{uuid4()}"),
                    "external_message_id": (f"phone-message-a-{uuid4()}"),
                    "external_customer_id": (f"provider-a-{uuid4()}"),
                    "customer_name": "Phone Buyer",
                    "customer_phone": phone_a,
                    "body": "First phone message",
                },
            )

            second = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": account_id,
                    "external_thread_id": (f"phone-thread-b-{uuid4()}"),
                    "external_message_id": (f"phone-message-b-{uuid4()}"),
                    "external_customer_id": (f"provider-b-{uuid4()}"),
                    "customer_name": "Phone Buyer",
                    "customer_phone": phone_b,
                    "body": "Second phone message",
                },
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            first_body = first.json()
            second_body = second.json()

            assert first_body["customer_id"] == second_body["customer_id"]

            conversation_ids.extend(
                [
                    first_body["conversation_id"],
                    second_body["conversation_id"],
                ]
            )

            customer_ids.append(first_body["customer_id"])

            async with SessionLocal() as db:
                identities = list(
                    (
                        await db.execute(
                            text(
                                """
                                SELECT
                                    identity_type,
                                    namespace,
                                    normalized_value
                                FROM cs_customer_identities
                                WHERE customer_id = :customer_id
                                ORDER BY
                                    identity_type,
                                    namespace,
                                    normalized_value
                                """
                            ),
                            {"customer_id": (first_body["customer_id"])},
                        )
                    ).all()
                )

                phone_rows = [row for row in identities if row.identity_type == "phone"]

                provider_rows = [
                    row
                    for row in identities
                    if row.identity_type == "provider_customer"
                ]

                assert len(phone_rows) == 1
                assert phone_rows[0].normalized_value == phone_a

                assert len(provider_rows) == 2

    finally:
        app.dependency_overrides.clear()

        if conversation_ids:
            await _cleanup(
                conversation_ids=conversation_ids,
                customer_ids=customer_ids,
            )


@pytest.mark.asyncio
async def test_provider_customer_identity_converges_without_email_or_phone():
    user = FakeUser()

    account_id = f"ig-account-{uuid4().hex}"
    external_customer_id = f"ig-customer-{uuid4().hex}"

    conversation_ids = []
    customer_ids = []

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "instagram",
                    "external_account_id": account_id,
                    "external_thread_id": (f"ig-thread-a-{uuid4()}"),
                    "external_message_id": (f"ig-message-a-{uuid4()}"),
                    "external_customer_id": (external_customer_id),
                    "customer_name": ("Instagram Customer"),
                    "body": "First Instagram message",
                },
            )

            second = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "instagram",
                    "external_account_id": account_id,
                    "external_thread_id": (f"ig-thread-b-{uuid4()}"),
                    "external_message_id": (f"ig-message-b-{uuid4()}"),
                    "external_customer_id": (external_customer_id),
                    "customer_name": ("Instagram Customer"),
                    "body": "Second Instagram message",
                },
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            assert first.json()["customer_id"] == second.json()["customer_id"]

            conversation_ids.extend(
                [
                    first.json()["conversation_id"],
                    second.json()["conversation_id"],
                ]
            )

            customer_ids.append(first.json()["customer_id"])

    finally:
        app.dependency_overrides.clear()

        if conversation_ids:
            await _cleanup(
                conversation_ids=conversation_ids,
                customer_ids=customer_ids,
            )


@pytest.mark.asyncio
async def test_pre_registry_email_customer_is_adopted_not_duplicated():
    user = FakeUser()

    email = f"legacy-{uuid4().hex}@example.com"

    conversation_ids = []
    customer_ids = []

    async with SessionLocal() as db:
        legacy = Customer(
            user_id=user.id,
            workspace_id=None,
            name="Legacy Customer",
            email=email,
        )

        db.add(legacy)
        await db.commit()
        await db.refresh(legacy)

        legacy_customer_id = legacy.id
        customer_ids.append(legacy.id)

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": (f"legacy-account-{uuid4()}"),
                    "external_thread_id": (f"legacy-thread-{uuid4()}"),
                    "external_message_id": (f"legacy-message-{uuid4()}"),
                    "external_customer_id": (f"legacy-provider-{uuid4()}"),
                    "customer_email": email.upper(),
                    "body": ("Legacy identity adoption"),
                },
            )

            assert response.status_code == 200, response.text

            body = response.json()

            assert body["customer_id"] == str(legacy_customer_id)

            conversation_ids.append(body["conversation_id"])

            async with SessionLocal() as db:
                count = await db.scalar(
                    select(func.count(Customer.id)).where(
                        Customer.user_id == user.id,
                        func.lower(Customer.email) == email,
                    )
                )

                assert count == 1

                identity_count = await db.scalar(
                    text(
                        """
                        SELECT count(*)
                        FROM cs_customer_identities
                        WHERE user_id = :user_id
                          AND customer_id =
                              :customer_id
                          AND identity_type =
                              'email'
                          AND normalized_value =
                              :email
                        """
                    ),
                    {
                        "user_id": user.id,
                        "customer_id": (legacy_customer_id),
                        "email": email,
                    },
                )

                assert identity_count == 1

    finally:
        app.dependency_overrides.clear()

        if conversation_ids:
            await _cleanup(
                conversation_ids=conversation_ids,
                customer_ids=customer_ids,
            )


@pytest.mark.asyncio
async def test_conflicting_identity_evidence_returns_409_without_auto_merge():
    user = FakeUser()

    email = f"conflict-{uuid4().hex}@example.com"

    phone_digits = str(10_000_000_000 + uuid4().int % 80_000_000_000)
    phone = f"+{phone_digits}"

    customer_ids = []

    async with SessionLocal() as db:
        email_customer = Customer(
            user_id=user.id,
            workspace_id=None,
            name="Email Customer",
            email=email,
        )

        phone_customer = Customer(
            user_id=user.id,
            workspace_id=None,
            name="Phone Customer",
            phone=phone,
        )

        db.add_all(
            [
                email_customer,
                phone_customer,
            ]
        )

        await db.commit()
        await db.refresh(email_customer)
        await db.refresh(phone_customer)

        customer_ids.extend(
            [
                email_customer.id,
                phone_customer.id,
            ]
        )

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": (f"conflict-account-{uuid4()}"),
                    "external_thread_id": (f"conflict-thread-{uuid4()}"),
                    "external_message_id": (f"conflict-message-{uuid4()}"),
                    "customer_email": email,
                    "customer_phone": phone,
                    "body": ("Conflicting identity evidence"),
                },
            )

            assert response.status_code == 409

            detail = response.json()["detail"]

            assert detail["code"] == "customer_identity_conflict"

            assert set(detail["customer_ids"]) == {
                str(customer_ids[0]),
                str(customer_ids[1]),
            }

            async with SessionLocal() as db:
                conversation_count = await db.scalar(
                    text(
                        """
                        SELECT count(*)
                        FROM cs_conversations
                        WHERE user_id = :user_id
                          AND customer_id =
                              ANY(
                                  CAST(
                                      :customer_ids
                                      AS uuid[]
                                  )
                              )
                        """
                    ),
                    {
                        "user_id": user.id,
                        "customer_ids": customer_ids,
                    },
                )

                assert conversation_count == 0

    finally:
        app.dependency_overrides.clear()

        if customer_ids:
            async with SessionLocal() as db:
                await db.execute(
                    text(
                        """
                        DELETE FROM cs_customers
                        WHERE id =
                            ANY(
                                CAST(
                                    :customer_ids
                                    AS uuid[]
                                )
                            )
                        """
                    ),
                    {"customer_ids": customer_ids},
                )

                await db.commit()
