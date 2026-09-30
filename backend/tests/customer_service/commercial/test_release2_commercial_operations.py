from __future__ import annotations

from datetime import datetime, timezone

import base64
import hashlib
import hmac
import json
import time
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.core.config import settings
from app.authentication.service import create_session
from app.core.session import SessionLocal
from app.domains.customer_service.services.commercial_operations import (
    CommercialOperationsService,
)
from app.domains.customer_service.models import (
    CustomerServiceAttachment,
    WorkspaceSubscription,
)
from app.workflow_operations.waits.schemas import WorkflowWaitCreate
from app.workflow_operations.waits.service import WorkflowWaitService
from app.identity import create_user
from app.main import app
from app.models.models import User as UserORM
from app.models.schemas import UserCreate
from app.tenancy.schemas import WorkspaceCreate, WorkspaceInvitationCreate
from app.tenancy.service import WorkspaceService


async def _mark_users_verified(*users) -> None:
    user_ids = [user.id for user in users if user is not None]

    if not user_ids:
        return

    async with SessionLocal() as db:
        await db.execute(
            update(UserORM)
            .where(UserORM.id.in_(user_ids))
            .values(
                email_verified_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()


async def _merchant(*, with_agent: bool = False):
    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"release2-owner-{uuid4()}@example.com",
                password=f"Release2-Owner-{uuid4()}",
                terms_accepted=True,
                terms_version="v1",
                privacy_accepted=True,
                privacy_version="v1",
            ),
            db,
        )
        workspace, _ = await WorkspaceService(db).create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(name=f"Release 2 {uuid4()}"),
        )
        agent = None
        if with_agent:
            agent = await create_user(
                UserCreate(
                    email=f"release2-agent-{uuid4()}@example.com",
                    password=f"Release2-Agent-{uuid4()}",
                    terms_accepted=True,
                    terms_version="v1",
                    privacy_accepted=True,
                    privacy_version="v1",
                ),
                db,
            )
            service = WorkspaceService(db)
            _, token = await service.create_invitation(
                workspace_id=workspace.id,
                actor_user_id=owner.id,
                payload=WorkspaceInvitationCreate(email=agent.email, role="agent"),
            )
            await service.accept_invitation(
                token=token, user_id=agent.id, user_email=agent.email
            )
    await _mark_users_verified(
        owner,
        agent,
    )

    return owner, workspace, agent


async def _headers(user, workspace):
    async with SessionLocal() as db:
        pair = await create_session(
            db,
            user=user,
            user_agent="pytest-session-fixture",
            ip_address="127.0.0.1",
        )

    return {
        "authorization": f"Bearer {pair.access_token}",
        "x-workspace-id": str(workspace.id),
    }


async def _conversation(client, headers, *, channel="website", suffix=""):
    customer = await client.post(
        "/customer-service/customers/",
        json={
            "name": f"Release 2 Customer {suffix}",
            "email": f"release2-{uuid4()}@example.com",
        },
        headers=headers,
    )
    assert customer.status_code == 200, customer.text
    conversation = await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer.json()["id"],
            "channel": channel,
            "subject": f"Commercial support {suffix}",
        },
        headers=headers,
    )
    assert conversation.status_code == 200, conversation.text
    return customer.json(), conversation.json()


@pytest.mark.asyncio
async def test_search_saved_view_and_idempotent_website_reply():
    owner, workspace, _ = await _merchant()
    headers = await _headers(owner, workspace)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, conversation = await _conversation(client, headers, suffix="searchable")
        reply = await client.post(
            f"/customer-service/conversations/{conversation['id']}/reply",
            json={"body": "Your order is on its way.", "idempotency_key": "reply-0001"},
            headers=headers,
        )
        replay = await client.post(
            f"/customer-service/conversations/{conversation['id']}/reply",
            json={"body": "Your order is on its way.", "idempotency_key": "reply-0001"},
            headers=headers,
        )
        assert reply.status_code == 200, reply.text
        assert replay.json()["message_id"] == reply.json()["message_id"]
        assert replay.json()["idempotent_replay"] is True

        search = await client.get(
            "/customer-service/search", params={"q": "searchable"}, headers=headers
        )
        assert search.status_code == 200
        assert search.json()[0]["conversation_id"] == conversation["id"]

        view = await client.post(
            "/customer-service/saved-views",
            json={"name": "Unassigned", "filters": {"unassigned": True}},
            headers=headers,
        )
        assert view.status_code == 201, view.text
        listed = await client.get("/customer-service/saved-views", headers=headers)
        assert [row["name"] for row in listed.json()] == ["Unassigned"]


@pytest.mark.asyncio
async def test_attachment_scan_download_and_presence_collision(tmp_path, monkeypatch):
    owner, workspace, agent = await _merchant(with_agent=True)
    monkeypatch.setattr(settings, "ATTACHMENT_STORAGE_ROOT", str(tmp_path))
    owner_headers = await _headers(owner, workspace)
    agent_headers = await _headers(agent, workspace)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, conversation = await _conversation(client, owner_headers)
        uploaded = await client.post(
            f"/customer-service/conversations/{conversation['id']}/attachments",
            files={"upload": ("proof.txt", b"safe proof", "text/plain")},
            headers=owner_headers,
        )
        assert uploaded.status_code == 201, uploaded.text
        downloaded = await client.get(
            f"/customer-service/attachments/{uploaded.json()['id']}/download",
            headers=agent_headers,
        )
        assert downloaded.content == b"safe proof"
        rejected = await client.post(
            f"/customer-service/conversations/{conversation['id']}/attachments",
            files={
                "upload": (
                    "virus.txt",
                    b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",
                    "text/plain",
                )
            },
            headers=owner_headers,
        )
        assert rejected.status_code == 422

        lease = await client.post(
            f"/customer-service/conversations/{conversation['id']}/presence",
            json={"ttl_seconds": 90},
            headers=owner_headers,
        )
        collision = await client.post(
            f"/customer-service/conversations/{conversation['id']}/presence",
            json={"ttl_seconds": 90},
            headers=agent_headers,
        )
        assert lease.status_code == 200
        assert collision.status_code == 409


@pytest.mark.asyncio
async def test_sla_holiday_calendar_resolution_and_public_csat():
    owner, workspace, _ = await _merchant()
    headers = await _headers(owner, workspace)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        calendar = await client.post(
            "/customer-service/sla/calendars",
            json={
                "name": "Tehran support",
                "timezone": "UTC",
                "weekly_hours": {
                    "mon": [["09:00", "17:00"]],
                    "tue": [["09:00", "17:00"]],
                },
                "holidays": ["2026-09-07"],
                "escalation_policy": {"before_breach_minutes": 30},
                "is_default": True,
            },
            headers=headers,
        )
        assert calendar.status_code == 201, calendar.text
        due = await client.get(
            f"/customer-service/sla/calendars/{calendar.json()['id']}/due-at",
            params={"start": "2026-09-07T10:00:00Z", "minutes": 60},
            headers=headers,
        )
        assert due.status_code == 200
        assert due.json()["due_at"].startswith("2026-09-08T10:00:00")

        _, conversation = await _conversation(client, headers)
        tickets = await client.get("/customer-service/tickets/", headers=headers)
        ticket = next(
            row
            for row in tickets.json()
            if row["conversation_id"] == conversation["id"]
        )
        resolved = await client.post(
            f"/customer-service/tickets/{ticket['id']}/resolve",
            json={
                "reason": "order_status_answered",
                "outcome": {"resolved_on_first_contact": True},
                "send_csat": True,
            },
            headers=headers,
        )
        assert resolved.status_code == 200, resolved.text
        answered = await client.post(
            "/customer-service/csat/respond",
            json={
                "token": resolved.json()["csat_token"],
                "score": 5,
                "comment": "Great",
            },
        )
        assert answered.status_code == 200
        report = await client.get("/customer-service/csat/report", headers=headers)
        assert report.json() == {"responses": 1, "average_score": 5.0}


@pytest.mark.asyncio
async def test_signed_billing_webhook_and_entitlements(monkeypatch):
    owner, workspace, _ = await _merchant()
    secret = "billing-test-secret"
    monkeypatch.setattr(settings, "BILLING_WEBHOOK_SECRET", secret)
    timestamp = str(int(time.time()))
    payload = json.dumps(
        {
            "id": f"evt_{uuid4()}",
            "type": "subscription.updated",
            "data": {
                "workspace_id": str(workspace.id),
                "plan": "growth",
                "status": "active",
                "entitlements": {
                    "agent_replies": True,
                    "attachments": True,
                    "saved_views": True,
                },
            },
        },
        separators=(",", ":"),
    ).encode()
    signature = hmac.new(
        secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256
    ).hexdigest()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        applied = await client.post(
            "/customer-service/billing/webhook",
            content=payload,
            headers={
                "content-type": "application/json",
                "x-billing-timestamp": timestamp,
                "x-billing-signature": signature,
            },
        )
        assert applied.status_code == 200, applied.text
        subscription = await client.get(
            "/customer-service/subscription", headers=(await _headers(owner, workspace))
        )
        assert subscription.json()["plan"] == "growth"
        assert subscription.json()["status"] == "active"


@pytest.mark.asyncio
async def test_verified_resend_inbound_is_replay_safe(monkeypatch):
    _, workspace, _ = await _merchant()
    secret_bytes = b"release2-resend-secret"
    monkeypatch.setattr(
        settings,
        "INBOUND_EMAIL_WEBHOOK_SECRET",
        "whsec_" + base64.b64encode(secret_bytes).decode(),
    )
    svix_id = f"msg_{uuid4()}"
    timestamp = str(int(time.time()))
    body = json.dumps(
        {
            "type": "email.received",
            "data": {
                "email_id": f"email_{uuid4()}",
                "from": "Customer <customer@example.com>",
                "to": ["support@example.com"],
                "subject": "Where is my order?",
                "text": "Please send tracking information.",
            },
        },
        separators=(",", ":"),
    ).encode()
    signed = f"{svix_id}.{timestamp}.{body.decode()}".encode()
    signature = base64.b64encode(
        hmac.new(secret_bytes, signed, hashlib.sha256).digest()
    ).decode()
    headers = {
        "content-type": "application/json",
        "svix-id": svix_id,
        "svix-timestamp": timestamp,
        "svix-signature": f"v1,{signature}",
    }
    url = f"/customer-service/inbox/email/webhooks/resend/{workspace.id}"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(url, content=body, headers=headers)
        replay = await client.post(url, content=body, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "processed"
    assert replay.json()["status"] == "duplicate"


@pytest.mark.asyncio
async def test_real_email_reply_adapter_is_idempotent(monkeypatch):
    owner, workspace, _ = await _merchant()
    calls = []

    def fake_send(*args, **kwargs):
        calls.append((args, kwargs))
        return {"id": "email_delivery_1"}

    monkeypatch.setattr(
        "app.domains.customer_service.services.messaging.send_email", fake_send
    )
    headers = await _headers(owner, workspace)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, conversation = await _conversation(client, headers, channel="email")
        url = f"/customer-service/conversations/{conversation['id']}/reply"
        payload = {"body": "We found your order.", "idempotency_key": "email-reply-1"}
        first = await client.post(url, json=payload, headers=headers)
        replay = await client.post(url, json=payload, headers=headers)
    assert first.status_code == 200, first.text
    assert replay.json()["idempotent_replay"] is True
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_merge_split_demo_consent_and_privacy_export():
    owner, workspace, _ = await _merchant()
    headers = await _headers(owner, workspace)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first_customer, first = await _conversation(client, headers, suffix="first")
        second_customer, second = await _conversation(client, headers, suffix="second")
        replied = await client.post(
            f"/customer-service/conversations/{first['id']}/reply",
            json={"body": "Message to split", "idempotency_key": "split-message-1"},
            headers=headers,
        )
        split = await client.post(
            f"/customer-service/conversations/{first['id']}/split",
            json={
                "message_ids": [replied.json()["message_id"]],
                "subject": "New issue",
            },
            headers=headers,
        )
        assert split.status_code == 200, split.text
        tickets = (
            await client.get("/customer-service/tickets/", headers=headers)
        ).json()
        assert any(
            row["conversation_id"] == split.json()["conversation_id"] for row in tickets
        )

        merged = await client.post(
            "/customer-service/conversations/merge",
            json={"source_id": first["id"], "target_id": second["id"]},
            headers=headers,
        )
        assert merged.status_code == 200, merged.text
        customer_merge = await client.post(
            "/customer-service/customers/merge",
            json={
                "source_id": first_customer["id"],
                "target_id": second_customer["id"],
            },
            headers=headers,
        )
        assert customer_merge.status_code == 200, customer_merge.text

        consent = await client.patch(
            f"/customer-service/customers/{second_customer['id']}/consent",
            json={"marketing": False, "support_processing": True, "source": "widget"},
            headers=headers,
        )
        assert consent.status_code == 200, consent.text
        assert consent.json()["consent"]["source"] == "widget"

        demo = await client.post(
            "/customer-service/onboarding/demo-data", headers=headers
        )
        replay_demo = await client.post(
            "/customer-service/onboarding/demo-data", headers=headers
        )
        assert demo.status_code == 201, demo.text
        assert replay_demo.json()["status"] == "already_seeded"

        privacy = await client.post(
            "/customer-service/privacy/requests",
            json={"customer_id": second_customer["id"], "kind": "export"},
            headers=headers,
        )
        assert privacy.status_code == 201, privacy.text
        async with SessionLocal() as db:
            completed = await CommercialOperationsService(
                db, workspace_id=workspace.id, actor_id=owner.id
            ).process_privacy_request(privacy.json()["id"])
        assert completed.status == "completed"
        assert completed.result["customer"]["consent"]["source"] == "widget"


@pytest.mark.asyncio
async def test_billing_rejects_invalid_signature_and_sla_policy_uses_calendar(
    monkeypatch,
):
    owner, workspace, _ = await _merchant()
    headers = await _headers(owner, workspace)
    monkeypatch.setattr(settings, "BILLING_WEBHOOK_SECRET", "configured-secret")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        rejected = await client.post(
            "/customer-service/billing/webhook",
            content=b"{}",
            headers={
                "content-type": "application/json",
                "x-billing-timestamp": str(int(time.time())),
                "x-billing-signature": "wrong",
            },
        )
        assert rejected.status_code == 401
        calendar = await client.post(
            "/customer-service/sla/calendars",
            json={
                "name": "Linked calendar",
                "timezone": "UTC",
                "weekly_hours": {"mon": [["09:00", "17:00"]]},
                "holidays": [],
                "escalation_policy": {"before_breach_minutes": 45},
            },
            headers=headers,
        )
        policy = await client.post(
            "/customer-service/sla/policies",
            json={
                "name": "Normal support",
                "priority": "normal",
                "first_response_minutes": 60,
                "resolution_minutes": 480,
                "calendar_id": calendar.json()["id"],
            },
            headers=headers,
        )
        assert policy.status_code == 200, policy.text
        assert policy.json()["calendar_id"] == calendar.json()["id"]


@pytest.mark.asyncio
async def test_workspace_quota_and_customer_service_approval_bridge():
    owner, workspace, _ = await _merchant()
    headers = await _headers(owner, workspace)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _conversation(client, headers, suffix="quota-first")
        async with SessionLocal() as db:
            subscription = await db.get(WorkspaceSubscription, workspace.id)
            subscription.entitlements = {
                **(subscription.entitlements or {}),
                "monthly_conversations": 1,
            }
            wait = await WorkflowWaitService(db).create(
                user_id=workspace.id,
                payload=WorkflowWaitCreate(
                    workflow_run_id=str(uuid4()),
                    node_id="merchant-approval",
                    wait_type="approval",
                    payload={"question": "Approve refund?"},
                ),
            )
            await db.commit()

        customer = await client.post(
            "/customer-service/customers/",
            json={"email": f"quota-{uuid4()}@example.com"},
            headers=headers,
        )
        blocked = await client.post(
            "/customer-service/conversations/",
            json={
                "customer_id": customer.json()["id"],
                "channel": "website",
                "subject": "Over quota",
            },
            headers=headers,
        )
        assert blocked.status_code == 429, blocked.text
        assert blocked.json()["detail"]["code"] == "monthly_conversation_quota_exceeded"

        approvals = await client.get(
            "/customer-service/workflow-approvals", headers=headers
        )
        assert approvals.status_code == 200, approvals.text
        assert approvals.json()[0]["id"] == str(wait.id)
        approved = await client.post(
            f"/customer-service/workflow-approvals/{wait.id}/approve",
            headers=headers,
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["approved"] is True
        assert approved.json()["resume_job_id"] is not None


@pytest.mark.asyncio
async def test_message_bound_attachment_validation_and_split_retargeting(
    tmp_path,
    monkeypatch,
):
    owner, workspace, _ = await _merchant()

    monkeypatch.setattr(
        settings,
        "ATTACHMENT_STORAGE_ROOT",
        str(tmp_path),
    )

    headers = await _headers(owner, workspace)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        _, source = await _conversation(
            client,
            headers,
            suffix="attachment-source",
        )

        _, other = await _conversation(
            client,
            headers,
            suffix="attachment-other",
        )

        reply = await client.post(
            (f"/customer-service/conversations/{source['id']}/reply"),
            json={
                "body": "Message with attachment",
                "idempotency_key": ("message-bound-attachment-1"),
            },
            headers=headers,
        )

        assert reply.status_code == 200, reply.text

        message_id = reply.json()["message_id"]

        linked = await client.post(
            (f"/customer-service/conversations/{source['id']}/attachments"),
            params={
                "message_id": message_id,
            },
            files={
                "upload": (
                    "linked.txt",
                    b"linked attachment",
                    "text/plain",
                )
            },
            headers=headers,
        )

        assert linked.status_code == 201, linked.text
        assert linked.json()["message_id"] == message_id

        unbound = await client.post(
            (f"/customer-service/conversations/{source['id']}/attachments"),
            files={
                "upload": (
                    "conversation.txt",
                    b"conversation attachment",
                    "text/plain",
                )
            },
            headers=headers,
        )

        assert unbound.status_code == 201, unbound.text
        assert unbound.json()["message_id"] is None

        wrong_conversation = await client.post(
            (f"/customer-service/conversations/{other['id']}/attachments"),
            params={
                "message_id": message_id,
            },
            files={
                "upload": (
                    "wrong.txt",
                    b"must not persist",
                    "text/plain",
                )
            },
            headers=headers,
        )

        assert wrong_conversation.status_code == 404

        split = await client.post(
            (f"/customer-service/conversations/{source['id']}/split"),
            json={
                "message_ids": [message_id],
                "subject": "Split attachment issue",
            },
            headers=headers,
        )

        assert split.status_code == 200, split.text

        split_conversation_id = UUID(split.json()["conversation_id"])

    async with SessionLocal() as db:
        linked_row = await db.get(
            CustomerServiceAttachment,
            UUID(linked.json()["id"]),
        )

        unbound_row = await db.get(
            CustomerServiceAttachment,
            UUID(unbound.json()["id"]),
        )

        assert linked_row is not None
        assert linked_row.message_id == UUID(message_id)
        assert linked_row.conversation_id == split_conversation_id

        assert unbound_row is not None
        assert unbound_row.message_id is None
        assert unbound_row.conversation_id == UUID(source["id"])
