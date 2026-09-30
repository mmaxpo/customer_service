from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_omnichannel_webhook_ingestion():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/customer-service/webhooks/omnichannel",
            json={
                "provider": "whatsapp",
                "payload": {
                    "message": "hello",
                },
            },
        )

        assert response.status_code == 404
