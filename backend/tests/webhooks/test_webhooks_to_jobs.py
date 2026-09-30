import hashlib
import hmac
import json
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


def _workflow():
    return {
        "nodes": [
            {
                "id": "t1",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "start",
                },
            },
            {
                "id": "r1",
                "data": {
                    "nodeType": "response",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "t1",
                "target": "r1",
            },
        ],
    }


@pytest.mark.asyncio
async def test_webhook_delivery_enqueues_workflow_job():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            endpoint = (
                await client.post(
                    "/webhooks/endpoints",
                    json={
                        "name": "Shopify orders",
                        "source": "shopify",
                        "config": {
                            "workflow": _workflow(),
                            "message": "webhook",
                        },
                    },
                )
            ).json()

            response = await client.post(
                f"/webhooks/{endpoint['id']}/orders.created",
                json={
                    "order_id": "1001",
                },
            )

            assert response.status_code == 200

            delivery = response.json()

            assert delivery["source"] == "shopify"
            assert delivery["event_type"] == "orders.created"
            assert delivery["job_id"] is not None
            assert delivery["status"] == "accepted"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_webhook_signature_required_when_secret_configured():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            endpoint = (
                await client.post(
                    "/webhooks/endpoints",
                    json={
                        "name": "Signed",
                        "source": "custom",
                        "secret": "secret-1",
                        "config": {
                            "workflow": _workflow(),
                            "message": "signed",
                        },
                    },
                )
            ).json()

            body = {"hello": "world"}

            missing = await client.post(
                f"/webhooks/{endpoint['id']}/event.received",
                json=body,
            )

            assert missing.status_code == 401

            raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
            signature = (
                "sha256="
                + hmac.new(
                    b"secret-1",
                    raw,
                    hashlib.sha256,
                ).hexdigest()
            )

            signed = await client.post(
                f"/webhooks/{endpoint['id']}/event.received",
                content=raw,
                headers={
                    "content-type": "application/json",
                    "x-tajeran-signature": signature,
                },
            )

            assert signed.status_code == 200
            assert signed.json()["job_id"] is not None

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_identical_webhook_redelivery_reuses_workflow_job():
    from sqlalchemy import select

    from app.core.session import SessionLocal
    from app.models.models import PlatformJob

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            endpoint_response = await client.post(
                "/webhooks/endpoints",
                json={
                    "name": "Duplicate delivery",
                    "source": "shopify",
                    "config": {
                        "workflow": _workflow(),
                        "message": "duplicate",
                    },
                },
            )

            assert endpoint_response.status_code == 200
            endpoint = endpoint_response.json()

            payload = {
                "id": 62001,
                "name": "#62001",
                "financial_status": "paid",
            }

            first = await client.post(
                f"/webhooks/{endpoint['id']}/orders/create",
                json=payload,
            )
            second = await client.post(
                f"/webhooks/{endpoint['id']}/orders/create",
                json=payload,
            )

        assert first.status_code == 200
        assert second.status_code == 200

        first_delivery = first.json()
        second_delivery = second.json()

        assert first_delivery["id"] != second_delivery["id"]
        assert first_delivery["job_id"] == second_delivery["job_id"]

        async with SessionLocal() as db:
            jobs = list(
                (
                    await db.execute(
                        select(PlatformJob).where(
                            PlatformJob.user_id == user.id,
                            PlatformJob.job_type == "workflow.run",
                        )
                    )
                )
                .scalars()
                .all()
            )

        matching = [
            job
            for job in jobs
            if (
                ((job.payload or {}).get("webhook") or {}).get("endpoint_id")
                == endpoint["id"]
                and ((job.payload or {}).get("webhook") or {}).get("external_id")
                == "62001"
            )
        ]

        assert len(matching) == 1
        assert matching[0].idempotency_key is not None
        assert matching[0].idempotency_key.startswith(
            f"webhook:v1:{endpoint['id']}:shopify:orders.created:"
        )

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_same_business_object_with_changed_webhook_body_creates_new_job():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            endpoint_response = await client.post(
                "/webhooks/endpoints",
                json={
                    "name": "Changed delivery",
                    "source": "shopify",
                    "config": {
                        "workflow": _workflow(),
                        "message": "changed",
                    },
                },
            )

            assert endpoint_response.status_code == 200
            endpoint = endpoint_response.json()

            first = await client.post(
                f"/webhooks/{endpoint['id']}/orders/updated",
                json={
                    "id": 62002,
                    "name": "#62002",
                    "financial_status": "pending",
                },
            )

            second = await client.post(
                f"/webhooks/{endpoint['id']}/orders/updated",
                json={
                    "id": 62002,
                    "name": "#62002",
                    "financial_status": "paid",
                },
            )

        assert first.status_code == 200
        assert second.status_code == 200

        assert first.json()["job_id"] != second.json()["job_id"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_webhook_endpoint_rejects_foreign_workflow_and_allows_owner():
    from sqlalchemy import delete, select

    from app.core.session import SessionLocal
    from app.models.models import WebhookEndpoint
    from app.runtime.workflows import build_runtime_workflow_repository

    owner = FakeUser()
    foreign = FakeUser()

    workflow_id = None
    created_endpoint_id = None

    try:
        # --------------------------------------------------------
        # Create one saved Runtime workflow owned by `owner`.
        # --------------------------------------------------------

        async with SessionLocal() as db:
            workflow_row = await build_runtime_workflow_repository(db).create(
                user_id=owner.id,
                name="CORE-6.4 webhook ownership",
                workflow=_workflow(),
            )
            workflow_id = workflow_row["id"]

        request_payload = {
            "name": "CORE-6.4 workflow reference",
            "source": "custom",
            "workflow_id": str(workflow_id),
            "secret": "core-6.4-secret",
            "config": {},
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # ----------------------------------------------------
            # Foreign user must not reference owner's workflow.
            # ----------------------------------------------------

            app.dependency_overrides[get_current_user] = lambda: foreign

            rejected = await client.post(
                "/webhooks/endpoints",
                json=request_payload,
            )

            assert rejected.status_code == 404
            assert rejected.json()["detail"] == "Workflow not found"

            async with SessionLocal() as db:
                foreign_rows = list(
                    (
                        await db.execute(
                            select(WebhookEndpoint).where(
                                WebhookEndpoint.user_id == foreign.id,
                                WebhookEndpoint.workflow_id == workflow_id,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

            assert foreign_rows == []

            # ----------------------------------------------------
            # Missing workflow uses identical not-found contract.
            # ----------------------------------------------------

            missing_payload = {
                **request_payload,
                "workflow_id": str(uuid4()),
            }

            missing = await client.post(
                "/webhooks/endpoints",
                json=missing_payload,
            )

            assert missing.status_code == 404
            assert missing.json()["detail"] == "Workflow not found"

            # ----------------------------------------------------
            # Owner can reference own workflow.
            # ----------------------------------------------------

            app.dependency_overrides[get_current_user] = lambda: owner

            accepted = await client.post(
                "/webhooks/endpoints",
                json=request_payload,
            )

            assert accepted.status_code == 200, accepted.text

            body = accepted.json()
            created_endpoint_id = body["id"]

            assert body["user_id"] == str(owner.id)
            assert body["workflow_id"] == str(workflow_id)
            assert body["status"] == "active"

    finally:
        app.dependency_overrides.pop(get_current_user, None)

        async with SessionLocal() as db:
            if created_endpoint_id is not None:
                await db.execute(
                    delete(WebhookEndpoint).where(
                        WebhookEndpoint.id == created_endpoint_id
                    )
                )
                await db.commit()

            if workflow_id is not None:
                await build_runtime_workflow_repository(db).delete(
                    user_id=owner.id,
                    workflow_id=workflow_id,
                )


@pytest.mark.asyncio
async def test_webhook_delivery_failure_rolls_back_workflow_job(monkeypatch):
    from sqlalchemy import select

    from app.core.session import SessionLocal
    from app.models.models import PlatformJob, WebhookDelivery
    from app.platform.webhooks.repository import WebhookRepository

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    endpoint_id = None

    async def fail_create_delivery(self, **kwargs):
        raise RuntimeError("forced webhook delivery persistence failure")

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            endpoint_response = await client.post(
                "/webhooks/endpoints",
                json={
                    "name": "Atomic webhook",
                    "source": "custom",
                    "config": {
                        "workflow": _workflow(),
                        "message": "atomic",
                    },
                },
            )

            assert endpoint_response.status_code == 200
            endpoint_id = endpoint_response.json()["id"]

            monkeypatch.setattr(
                WebhookRepository,
                "create_delivery",
                fail_create_delivery,
            )

            with pytest.raises(
                RuntimeError,
                match="forced webhook delivery persistence failure",
            ):
                await client.post(
                    f"/webhooks/{endpoint_id}/event.received",
                    json={
                        "id": "atomic-event",
                        "value": "test",
                    },
                )

        # Fresh session proves the failed request left no durable job
        # and no delivery.
        async with SessionLocal() as db:
            jobs = list(
                (
                    await db.execute(
                        select(PlatformJob).where(
                            PlatformJob.user_id == user.id,
                            PlatformJob.job_type == "workflow.run",
                        )
                    )
                )
                .scalars()
                .all()
            )

            deliveries = list(
                (
                    await db.execute(
                        select(WebhookDelivery).where(
                            WebhookDelivery.endpoint_id == endpoint_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

        matching_jobs = [
            job
            for job in jobs
            if (
                ((job.payload or {}).get("webhook") or {}).get("endpoint_id")
                == endpoint_id
            )
        ]

        assert matching_jobs == []
        assert deliveries == []

    finally:
        app.dependency_overrides.pop(get_current_user, None)
