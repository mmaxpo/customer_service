import hashlib
import hmac
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.secrets import decrypt_secret, encrypt_secret
from app.platform.jobs.service import JobService
from app.platform.webhooks.providers.registry import WebhookProviderRegistry
from app.platform.webhooks.repository import WebhookRepository
from app.runtime.workflows import build_runtime_workflow_repository


class WebhookService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        provider_registry: WebhookProviderRegistry | None = None,
    ):
        self.db = db
        self.repo = WebhookRepository(db)
        self.jobs = JobService(db)

        if provider_registry is None:
            from app.platform.composition import (
                build_default_webhook_provider_registry,
            )

            provider_registry = build_default_webhook_provider_registry()

        self.provider_registry = provider_registry

    async def create_endpoint(self, *, user_id, payload):
        if payload.workflow_id is not None:
            workflow = await build_runtime_workflow_repository(self.db).get(
                user_id=user_id,
                workflow_id=payload.workflow_id,
            )
            if workflow is None:
                raise HTTPException(status_code=404, detail="Workflow not found")

        return await self.repo.create_endpoint(
            user_id=user_id,
            name=payload.name,
            source=payload.source.strip().lower(),
            workflow_id=payload.workflow_id,
            secret=encrypt_secret(payload.secret),
            config=payload.config,
        )

    async def list_endpoints(self, *, user_id):
        return await self.repo.list_endpoints(user_id=user_id)

    async def receive(
        self,
        *,
        endpoint_id: UUID,
        event_type: str,
        payload: dict,
        headers: dict,
        raw_body: bytes | None = None,
    ):
        endpoint = await self.repo.get_endpoint(endpoint_id=endpoint_id)

        if endpoint is None or endpoint.status != "active":
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")

        self._verify_signature(
            endpoint=endpoint,
            headers=headers,
            raw_body=raw_body or b"",
        )

        adapter = self.provider_registry.get(endpoint.source)

        normalized = adapter.normalize(
            event_type=event_type,
            payload=payload,
            headers=headers,
        )

        job_payload = {
            "webhook": {
                "endpoint_id": str(endpoint.id),
                "source": normalized.source,
                "event_type": normalized.event_type,
                "external_id": normalized.external_id,
                "payload": normalized.normalized_payload,
                "raw_payload": normalized.raw_payload,
                "headers": normalized.headers,
            },
            **(endpoint.config or {}),
        }

        if endpoint.workflow_id is not None:
            job_payload["workflow_id"] = str(endpoint.workflow_id)

        if "workflow" not in job_payload and "workflow_id" not in job_payload:
            await self.repo.create_delivery(
                endpoint=endpoint,
                event_type=normalized.event_type,
                payload=normalized.normalized_payload,
                headers=headers,
                status="rejected",
                error_message="Endpoint has no workflow or workflow_id configured",
            )
            raise HTTPException(
                status_code=422, detail="Endpoint has no workflow configured"
            )

        provider_event_id = normalized.provider_event_id

        if provider_event_id is not None:
            delivery_identity = f"provider:{provider_event_id}"
        else:
            body_digest = hashlib.sha256(raw_body or b"").hexdigest()
            delivery_identity = f"body-sha256:{body_digest}"

        idempotency_key = (
            "webhook:v1:"
            f"{endpoint.id}:"
            f"{normalized.source}:"
            f"{normalized.event_type}:"
            f"{delivery_identity}"
        )

        job = await self.jobs.enqueue(
            user_id=endpoint.user_id,
            job_type="workflow.run",
            payload=job_payload,
            max_attempts=3,
            idempotency_key=idempotency_key,
            commit=False,
        )

        delivery = await self.repo.create_delivery(
            endpoint=endpoint,
            event_type=event_type,
            payload=payload,
            headers=headers,
            job_id=job.id,
            status="accepted",
        )

        return delivery

    def _verify_signature(self, *, endpoint, headers: dict, raw_body: bytes) -> None:
        if not endpoint.secret:
            return

        signature = headers.get("x-tajeran-signature") or headers.get(
            "X-Tajeran-Signature"
        )

        if not signature:
            raise HTTPException(status_code=401, detail="Missing webhook signature")

        secret = decrypt_secret(endpoint.secret)
        if not secret:
            return

        expected = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        expected_header = f"sha256={expected}"

        if not hmac.compare_digest(signature, expected_header):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
