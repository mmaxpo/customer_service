from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import get_db
from app.main import app
from app.platform.jobs.service import JobService


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
async def test_shopify_webhook_delivery_enqueues_normalized_payload():
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
                        "name": "Shopify",
                        "source": "shopify",
                        "config": {
                            "workflow": _workflow(),
                            "message": "shopify webhook",
                        },
                    },
                )
            ).json()

            response = await client.post(
                f"/webhooks/{endpoint['id']}/orders/create",
                json={
                    "id": 1001,
                    "name": "#1001",
                    "email": "buyer@example.com",
                    "financial_status": "paid",
                },
            )

            assert response.status_code == 200, response.text

            delivery = response.json()
            job_id = delivery["job_id"]

            async for db in get_db():
                job = await JobService(db).get(
                    job_id=job_id,
                    user_id=user.id,
                )

                webhook = job.payload["webhook"]

                assert webhook["source"] == "shopify"
                assert webhook["event_type"] == "orders.created"
                assert webhook["external_id"] == "1001"
                assert webhook["payload"]["order_name"] == "#1001"
                assert webhook["payload"]["customer_email"] == "buyer@example.com"

                break

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_generic_webhook_sources_are_preserved_in_workflow_job():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            for source in ("custom", "acme"):
                endpoint_response = await client.post(
                    "/webhooks/endpoints",
                    json={
                        "name": f"Source {source}",
                        "source": source,
                        "config": {
                            "workflow": _workflow(),
                            "message": source,
                        },
                    },
                )

                assert endpoint_response.status_code == 200
                endpoint = endpoint_response.json()

                response = await client.post(
                    f"/webhooks/{endpoint['id']}/event.received",
                    json={
                        "id": f"{source}-event",
                        "value": source,
                    },
                )

                assert response.status_code == 200, response.text

                delivery = response.json()

                async for db in get_db():
                    job = await JobService(db).get(
                        job_id=delivery["job_id"],
                        user_id=user.id,
                    )

                    webhook = job.payload["webhook"]

                    assert endpoint["source"] == source
                    assert webhook["source"] == source
                    assert webhook["event_type"] == "event.received"
                    assert webhook["external_id"] == f"{source}-event"
                    assert webhook["raw_payload"] == {
                        "id": f"{source}-event",
                        "value": source,
                    }

                    break

    finally:
        app.dependency_overrides.pop(get_current_user, None)
