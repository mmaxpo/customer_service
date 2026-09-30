from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import Customer
from app.main import app


class FakeUser:
    def __init__(self, *, email: str):
        self.id = uuid4()
        self.email = email


@pytest.mark.asyncio
async def test_customer_create_normalizes_email_and_rejects_duplicate():
    user = FakeUser(email="identity-owner@example.com")
    email = f"Identity-{uuid4().hex}@Example.COM"

    app.dependency_overrides[get_current_user] = lambda: user

    created_ids = []

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Identity Customer",
                    "email": f"  {email}  ",
                },
            )

            assert first.status_code == 200, first.text

            first_body = first.json()
            created_ids.append(first_body["id"])

            normalized = email.strip().lower()

            assert first_body["email"] == normalized

            duplicate = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Duplicate Identity",
                    "email": normalized.upper(),
                },
            )

            assert duplicate.status_code == 409
            assert duplicate.json() == {
                "detail": ("customer with this email already exists")
            }

            async with SessionLocal() as db:
                count = await db.scalar(
                    select(func.count(Customer.id)).where(
                        Customer.user_id == user.id,
                        func.lower(Customer.email) == normalized,
                    )
                )

                assert count == 1

    finally:
        app.dependency_overrides.clear()

        if created_ids:
            async with SessionLocal() as db:
                await db.execute(delete(Customer).where(Customer.id.in_(created_ids)))
                await db.commit()


@pytest.mark.asyncio
async def test_same_email_is_allowed_for_different_users():
    first_user = FakeUser(
        email="tenant-a@example.com",
    )
    second_user = FakeUser(
        email="tenant-b@example.com",
    )

    email = f"{uuid4().hex}@example.com"
    created_ids = []

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            app.dependency_overrides[get_current_user] = lambda: first_user

            first = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Tenant A Customer",
                    "email": email,
                },
            )

            assert first.status_code == 200, first.text
            created_ids.append(first.json()["id"])

            app.dependency_overrides[get_current_user] = lambda: second_user

            second = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Tenant B Customer",
                    "email": email,
                },
            )

            assert second.status_code == 200, second.text
            created_ids.append(second.json()["id"])

    finally:
        app.dependency_overrides.clear()

        if created_ids:
            async with SessionLocal() as db:
                await db.execute(delete(Customer).where(Customer.id.in_(created_ids)))
                await db.commit()


@pytest.mark.asyncio
async def test_explicit_empty_customer_is_rejected():
    user = FakeUser(email="empty-customer@example.com")

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/customers/",
                json={},
            )

            assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_non_email_customer_remains_allowed():
    user = FakeUser(email="anonymous-customer@example.com")
    created_id = None

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Anonymous Website Visitor",
                },
            )

            assert response.status_code == 200, response.text
            assert response.json()["email"] is None

            created_id = response.json()["id"]

    finally:
        app.dependency_overrides.clear()

        if created_id is not None:
            async with SessionLocal() as db:
                await db.execute(delete(Customer).where(Customer.id == created_id))
                await db.commit()


@pytest.mark.asyncio
async def test_concurrent_same_tenant_customer_create_serializes():
    user = FakeUser(
        email="customer-concurrency@example.com",
    )

    email = f"{uuid4().hex}@example.com"
    created_ids = []

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first, second = await asyncio.gather(
                client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Concurrent Customer A",
                        "email": email,
                    },
                ),
                client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Concurrent Customer B",
                        "email": email.upper(),
                    },
                ),
            )

            statuses = sorted(
                [
                    first.status_code,
                    second.status_code,
                ]
            )

            assert statuses == [200, 409]

            successful = first if first.status_code == 200 else second

            created_ids.append(successful.json()["id"])

            async with SessionLocal() as db:
                count = await db.scalar(
                    select(func.count(Customer.id)).where(
                        Customer.user_id == user.id,
                        func.lower(Customer.email) == email.lower(),
                    )
                )

                assert count == 1

    finally:
        app.dependency_overrides.clear()

        if created_ids:
            async with SessionLocal() as db:
                await db.execute(delete(Customer).where(Customer.id.in_(created_ids)))
                await db.commit()
