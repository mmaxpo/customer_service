from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.domains.customer_service.services.shopify import ShopifyService
from app.main import app
from app.platform.jobs.worker import JobWorker
from app.workflow_operations.waits.service import WorkflowWaitService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "complex-intake@example.com"


async def install_verified_shopify_for_user(user_id) -> None:
    """
    Provision Shopify through the real installation lifecycle so semantic
    ecommerce capabilities may select the Shopify binding in E2E tests.
    """
    from app.core.session import SessionLocal

    class FakeShopifyVerificationProvider:
        async def verify_connection(
            self,
            *,
            shop_domain,
            access_token,
        ):
            return {
                "id": f"support-e2e-{user_id}",
                "name": "Support E2E Shop",
                "myshopify_domain": shop_domain,
            }

    async with SessionLocal() as installation_db:
        installation_service = ShopifyService(
            installation_db,
            provider=FakeShopifyVerificationProvider(),
        )

        connection = await installation_service.connect(
            user_id=user_id,
            shop_domain="support-e2e.myshopify.com",
            access_token="support-e2e-token",
        )

        assert connection.status == "active"

        verification = await installation_service.test_connection(
            user_id=user_id,
        )

        assert verification["ok"] is True


COMPLEX_MESSAGE = (
    "I received both items damaged in order #1003. "
    "I want one item refunded and the other replaced. "
    "Please send the replacement to my new address. "
    "This is urgent."
)


@pytest.mark.asyncio
async def test_complex_incomplete_request_clarifies_before_workflow_dispatch(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    await install_verified_shopify_for_user(user.id)

    provider_calls = {
        "get_order": 0,
        "perform_order_action": 0,
    }

    async def fake_get_order(self, *, user_id, order_ref):
        provider_calls["get_order"] += 1

        assert user_id == user.id
        assert order_ref == "1003"

        return {
            "order_id": "6992274227367",
            "order_name": "#1003",
            "payload": {
                "id": "6992274227367",
                "name": "#1003",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "line_items": [
                    {
                        "id": "101",
                        "title": "Snowboard",
                        "variant_title": "158 cm",
                        "quantity": 1,
                    },
                    {
                        "id": "102",
                        "title": "Snowboard Boots",
                        "variant_title": "Size 10",
                        "quantity": 1,
                    },
                ],
            },
            "context": {},
            "summary": {},
        }

    async def forbidden_perform_order_action(self, **kwargs):
        provider_calls["perform_order_action"] += 1
        raise AssertionError(
            "Complex incomplete intake must not perform a Shopify mutation"
        )

    monkeypatch.setattr(
        ShopifyService,
        "get_order",
        fake_get_order,
    )
    monkeypatch.setattr(
        ShopifyService,
        "perform_order_action",
        forbidden_perform_order_action,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            assert settings.status_code == 200
            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200
            session = session_response.json()

            response = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session['id']}/messages"
                ),
                json={
                    "content": COMPLEX_MESSAGE,
                    "client_message_id": f"complex-{uuid4()}",
                },
            )

            assert response.status_code == 200, response.text
            body = response.json()

            assert body["support_intake"]["handled"] is True
            assert body["support_intake"]["requires_clarification"] is True
            assert body["support_intake"]["mutation_allowed"] is False

            assert body["workflow_dispatch"]["enqueued"] == []

            assert provider_calls == {
                "get_order": 1,
                "perform_order_action": 0,
            }

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            review_jobs = [
                job
                for job in jobs.json()
                if (
                    job["job_type"] == "workflow.run"
                    and job["payload"].get("extras", {}).get("support_review")
                    is not None
                )
            ]

            assert review_jobs == []

            messages = await client.get(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session['id']}/messages"
                )
            )
            assert messages.status_code == 200

            assistant_messages = [
                message for message in messages.json() if message["role"] == "assistant"
            ]

            assert len(assistant_messages) == 1

            clarification = assistant_messages[0]["content"]

            assert "I found order #1003" in clarification
            assert "Snowboard — 158 cm" in clarification
            assert "Snowboard Boots — Size 10" in clarification
            assert "Which item would you like refunded?" in clarification
            assert "Which item would you like replaced?" in clarification
            assert "What address should we use" in clarification

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            matching_jobs = [
                job
                for job in jobs.json()
                if job["job_type"] == "workflow.run"
                and job["payload"].get("message") == COMPLEX_MESSAGE
            ]

            assert matching_jobs == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_complex_intake_retry_replays_without_second_clarification(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    await install_verified_shopify_for_user(user.id)

    provider_calls = {
        "get_order": 0,
        "perform_order_action": 0,
    }

    async def fake_get_order(self, *, user_id, order_ref):
        provider_calls["get_order"] += 1

        assert user_id == user.id
        assert order_ref == "1003"

        return {
            "order_id": "6992274227367",
            "order_name": "#1003",
            "payload": {
                "id": "6992274227367",
                "name": "#1003",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "line_items": [
                    {
                        "id": "101",
                        "title": "Snowboard",
                        "variant_title": "158 cm",
                        "quantity": 1,
                    },
                    {
                        "id": "102",
                        "title": "Snowboard Boots",
                        "variant_title": "Size 10",
                        "quantity": 1,
                    },
                ],
            },
            "context": {},
            "summary": {},
        }

    async def forbidden_perform_order_action(self, **kwargs):
        provider_calls["perform_order_action"] += 1
        raise AssertionError("Complex clarification replay must never mutate Shopify")

    monkeypatch.setattr(
        ShopifyService,
        "get_order",
        fake_get_order,
    )
    monkeypatch.setattr(
        ShopifyService,
        "perform_order_action",
        forbidden_perform_order_action,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            assert settings.status_code == 200
            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200
            session = session_response.json()

            client_message_id = f"complex-replay-{uuid4()}"
            url = (
                f"/customer-service/chat/public/{public_key}"
                f"/sessions/{session['id']}/messages"
            )
            payload = {
                "content": COMPLEX_MESSAGE,
                "client_message_id": client_message_id,
            }

            first = await client.post(url, json=payload)
            second = await client.post(url, json=payload)

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            first_body = first.json()
            second_body = second.json()

            assert first_body["idempotent_replay"] is False
            assert second_body["idempotent_replay"] is True

            assert second_body["id"] == first_body["id"]
            assert second_body["event_id"] == first_body["event_id"]
            assert second_body["workflow_dispatch"] == first_body["workflow_dispatch"]
            assert second_body["support_intake"] == first_body["support_intake"]

            assert first_body["support_intake"]["handled"] is True
            assert first_body["support_intake"]["requires_clarification"] is True
            assert first_body["support_intake"]["mutation_allowed"] is False

            assert provider_calls == {
                "get_order": 1,
                "perform_order_action": 0,
            }

            messages = await client.get(url)
            assert messages.status_code == 200

            customer_messages = [
                message
                for message in messages.json()
                if message["role"] == "customer"
                and message["content"] == COMPLEX_MESSAGE
            ]
            assistant_messages = [
                message
                for message in messages.json()
                if message["role"] == "assistant"
                and "Which item would you like refunded?" in message["content"]
            ]

            assert len(customer_messages) == 1
            assert len(assistant_messages) == 1

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            matching_jobs = [
                job
                for job in jobs.json()
                if job["job_type"] == "workflow.run"
                and job["payload"].get("message") == COMPLEX_MESSAGE
            ]

            assert matching_jobs == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_complex_intake_persists_pending_objective(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    await install_verified_shopify_for_user(user.id)

    async def fake_get_order(self, *, user_id, order_ref):
        return {
            "order_id": "6992274227367",
            "order_name": "#1003",
            "payload": {
                "id": "6992274227367",
                "name": "#1003",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "line_items": [
                    {
                        "id": "101",
                        "title": "Snowboard",
                        "variant_title": "158 cm",
                        "quantity": 1,
                    },
                    {
                        "id": "102",
                        "title": "Snowboard Boots",
                        "variant_title": "Size 10",
                        "quantity": 1,
                    },
                ],
            },
            "context": {},
            "summary": {},
        }

    monkeypatch.setattr(
        ShopifyService,
        "get_order",
        fake_get_order,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            session_id = session_response.json()["id"]

            response = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": COMPLEX_MESSAGE,
                    "client_message_id": f"pending-{uuid4()}",
                },
            )

            assert response.status_code == 200
            assert (
                response.json()["support_intake"]["pending_status"]
                == "awaiting_customer"
            )

        from uuid import UUID

        from app.core.session import SessionLocal
        from app.domains.customer_service.repositories.chat_repository import (
            ChatRepository,
        )

        async with SessionLocal() as db:
            session = await ChatRepository(db).get_session(session_id=UUID(session_id))

            pending = (session.meta or {})["pending_support_objective"]

            assert pending["version"] == 1
            assert pending["status"] == "awaiting_customer"
            assert pending["order"]["provider"] == "shopify"
            assert pending["order"]["order_ref"] == "#1003"

            assert pending["objective"]["order_ref"] == "1003"
            assert pending["objective"]["mutation_allowed"] is False
            assert pending["objective"]["missing_information"] == [
                "refund_item",
                "replacement_item",
                "replacement_address",
            ]

            assert pending["original_message_id"]
            assert pending["clarification_message_id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


CLARIFICATION_MESSAGE = (
    "Refund the Snowboard and replace the Snowboard Boots. "
    "Send the replacement to: "
    "123 Main Street, Miami, FL 33101."
)


@pytest.mark.asyncio
async def test_pending_complex_objective_resumes_from_customer_clarification(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    provider_calls = {
        "get_order": 0,
        "perform_order_action": 0,
    }
    action_calls = []

    async def fake_get_order(self, *, user_id, order_ref):
        provider_calls["get_order"] += 1

        assert user_id == user.id
        assert order_ref == "1003"

        return {
            "order_id": "6992274227367",
            "order_name": "#1003",
            "payload": {
                "id": "6992274227367",
                "name": "#1003",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "line_items": [
                    {
                        "id": "101",
                        "title": "Snowboard",
                        "variant_title": "158 cm",
                        "quantity": 1,
                    },
                    {
                        "id": "102",
                        "title": "Snowboard Boots",
                        "variant_title": "Size 10",
                        "quantity": 1,
                    },
                ],
            },
            "context": {},
            "summary": {},
        }

    async def capture_perform_order_action(
        self,
        *,
        user_id,
        action,
        order_ref,
        reason=None,
        note=None,
        new_address=None,
        amount=None,
        scope=None,
        idempotency_key=None,
        approval_wait_id=None,
        workflow_run_id=None,
    ):
        provider_calls["perform_order_action"] += 1

        call = {
            "user_id": user_id,
            "action": action,
            "order_ref": order_ref,
            "reason": reason,
            "note": note,
            "new_address": new_address,
            "amount": amount,
            "scope": scope,
            "idempotency_key": idempotency_key,
            "approval_wait_id": approval_wait_id,
            "workflow_run_id": workflow_run_id,
        }
        action_calls.append(call)

        # Test seam ends at ShopifyService. Nothing below this
        # point reaches a provider or performs a real mutation.
        return {
            "status": "prepared",
            "prepared_only": True,
            "action": action,
            "order_ref": order_ref,
            "scope": scope or {},
            "idempotency_key": idempotency_key,
        }

    monkeypatch.setattr(
        ShopifyService,
        "get_order",
        fake_get_order,
    )
    monkeypatch.setattr(
        ShopifyService,
        "perform_order_action",
        capture_perform_order_action,
    )

    from app.core.session import SessionLocal
    from app.runtime.capabilities.execution.installation.repository import (
        DatabaseProviderInstallationReader,
    )

    class FakeShopifyVerificationProvider:
        async def verify_connection(
            self,
            *,
            shop_domain,
            access_token,
        ):
            assert shop_domain == "support-e2e.myshopify.com"
            assert access_token == "support-e2e-token"

            return {
                "id": "support-e2e-shop",
                "name": "Support E2E Shop",
                "myshopify_domain": shop_domain,
            }

    # Reproduce the real Shopify installation lifecycle:
    #
    # connect()
    #   -> configured/authenticated/unverified
    #
    # test_connection()
    #   -> configured/authenticated/verified
    #   -> semantic provider becomes available
    async with SessionLocal() as installation_db:
        installation_service = ShopifyService(
            installation_db,
            provider=FakeShopifyVerificationProvider(),
        )

        connection = await installation_service.connect(
            user_id=user.id,
            shop_domain="support-e2e.myshopify.com",
            access_token="support-e2e-token",
        )

        assert connection.status == "active"

        connected_snapshot = await DatabaseProviderInstallationReader(
            installation_db
        ).get_provider_installation(
            user_id=user.id,
            tenant_id=None,
            provider_id="shopify",
        )

        assert connected_snapshot.found is True
        assert connected_snapshot.enabled is True
        assert connected_snapshot.available is False

        verification = await installation_service.test_connection(
            user_id=user.id,
        )

        assert verification["ok"] is True

        verified_snapshot = await DatabaseProviderInstallationReader(
            installation_db
        ).get_provider_installation(
            user_id=user.id,
            tenant_id=None,
            provider_id="shopify",
        )

        assert verified_snapshot.found is True
        assert verified_snapshot.enabled is True
        assert verified_snapshot.available is True

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            assert settings.status_code == 200
            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200
            session_id = session_response.json()["id"]

            first = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": COMPLEX_MESSAGE,
                    "client_message_id": f"initial-{uuid4()}",
                },
            )

            assert first.status_code == 200, first.text
            assert (
                first.json()["support_intake"]["pending_status"] == "awaiting_customer"
            )

            second = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": CLARIFICATION_MESSAGE,
                    "client_message_id": f"clarification-{uuid4()}",
                },
            )

            assert second.status_code == 200, second.text
            body = second.json()

            assert body["support_intake"]["handled"] is True
            assert body["support_intake"]["continued"] is True
            assert body["support_intake"]["pending_status"] == "ready_for_review"

            review_plan_id = body["support_intake"]["review_plan_id"]
            review_plan = body["support_intake"]["review_plan"]
            review_workflow_job_id = body["support_intake"]["review_workflow_job_id"]

            assert review_plan_id
            assert review_workflow_job_id
            assert body["support_intake"]["review_workflow_job_status"] == "queued"
            assert review_plan["status"] == "awaiting_human_review"
            assert review_plan["approval_required"] is True
            assert review_plan["execution_allowed"] is False
            assert [
                operation["operation_type"] for operation in review_plan["operations"]
            ] == [
                "partial_refund",
                "replacement",
                "replacement_address",
            ]
            assert body["support_intake"]["requires_clarification"] is False
            assert body["support_intake"]["mutation_allowed"] is False

            objective = body["support_intake"]["objective"]

            assert objective["item_assignments"] == {
                "refund_item": "101",
                "replacement_item": "102",
            }
            assert objective["replacement_address"] == {
                "formatted": "123 Main Street, Miami, FL 33101"
            }
            assert objective["missing_information"] == []

            assert body["workflow_dispatch"]["enqueued"] == []

            assert provider_calls == {
                "get_order": 1,
                "perform_order_action": 0,
            }

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            review_jobs = [
                job
                for job in jobs.json()
                if (
                    job["job_type"] == "workflow.run"
                    and job["payload"]
                    .get("extras", {})
                    .get("support_review", {})
                    .get("review_plan_id")
                    == review_plan_id
                )
            ]

            assert len(review_jobs) == 1

            review_job = review_jobs[0]

            assert review_job["id"] == review_workflow_job_id
            assert review_job["status"] == "queued"

            support_review = review_job["payload"]["extras"]["support_review"]

            assert support_review["review_plan_id"] == review_plan_id
            assert support_review["review_plan"] == review_plan

            from uuid import UUID

            async with SessionLocal() as worker_db:
                processed_review_job = await JobWorker(
                    worker_db,
                    worker_id=("support-review-approval-boundary"),
                ).run_once(job_id=UUID(review_workflow_job_id))

                assert processed_review_job is not None
                assert str(processed_review_job.id) == review_workflow_job_id

                # A paused workflow is a successfully processed
                # platform job. The workflow result itself records
                # the pause boundary.
                assert processed_review_job.status == "succeeded"
                assert processed_review_job.result["meta"]["status"] == "paused"

                workflow_run_id = processed_review_job.result["meta"]["workflow_run_id"]

                waits = await WorkflowWaitService(worker_db).list_for_user(
                    user_id=user.id,
                    status="waiting",
                    workflow_run_id=workflow_run_id,
                )

                approval_waits = [
                    wait
                    for wait in waits
                    if (wait.wait_type == "approval" and wait.node_id == "approval")
                ]

                assert len(approval_waits) == 1

                approval_wait = approval_waits[0]

                assert approval_wait.status == "waiting"
                assert approval_wait.workflow_run_id == workflow_run_id

                wait_context = approval_wait.payload["context"]

                assert wait_context["review_plan_id"] == review_plan_id
                assert wait_context["review_plan"] == review_plan

                assert approval_wait.payload["context_key"] == "support_review"
                assert approval_wait.payload["question"] == (
                    "Approve this customer-support resolution plan?"
                )

                # Nothing has crossed the human gate yet.
                assert provider_calls["perform_order_action"] == 0
                assert action_calls == []

                approval_response = await client.post(
                    f"/workflow-waits/{approval_wait.id}/approve"
                )

                assert approval_response.status_code == 200, approval_response.text

                approval_body = approval_response.json()

                assert approval_body["approved"] is True
                assert approval_body["status"] == "resolved"
                assert approval_body["workflow_run_id"] == (workflow_run_id)
                assert approval_body["resume_job_id"]

                resume_job_id = approval_body["resume_job_id"]

                resumed_job = await JobWorker(
                    worker_db,
                    worker_id=("support-review-approved-resume"),
                ).run_once(job_id=UUID(resume_job_id))

                assert resumed_job is not None
                assert str(resumed_job.id) == resume_job_id
                assert resumed_job.status == "succeeded", {
                    "status": resumed_job.status,
                    "error_message": resumed_job.error_message,
                    "result": resumed_job.result,
                    "attempts": resumed_job.attempts,
                    "max_attempts": resumed_job.max_attempts,
                }
                assert resumed_job.result["meta"]["status"] == "ok"

                # The approval wait must remain durably resolved.
                async with SessionLocal() as verification_db:
                    resolved_wait = await WorkflowWaitService(
                        verification_db
                    ).get_for_user(
                        user_id=user.id,
                        wait_id=approval_wait.id,
                    )

                    assert resolved_wait.status == "resolved"
                    assert resolved_wait.resolution == {
                        "approved": True,
                        "action": "approved",
                    }

            # Before approval we proved zero action calls.
            # After approval the workflow must prepare exactly
            # the two reviewed business operations.
            assert provider_calls == {
                "get_order": 1,
                "perform_order_action": 2,
            }
            assert len(action_calls) == 2

            actions_by_type = {call["action"]: call for call in action_calls}

            assert set(actions_by_type) == {
                "refund",
                "reship",
            }

            refund_call = actions_by_type["refund"]

            assert refund_call["user_id"] == user.id
            assert refund_call["order_ref"] == "#1003"
            assert refund_call["scope"] == {
                "line_items": [
                    {
                        "line_item_id": "101",
                        "quantity": 1,
                        "amount": None,
                    }
                ],
                "replacement_line_item_id": None,
                "replacement_quantity": None,
                "new_address": None,
            }
            assert refund_call["idempotency_key"] == (
                f"support-review:{review_plan_id}:partial-refund"
            )

            replacement_call = actions_by_type["reship"]

            assert replacement_call["user_id"] == user.id
            assert replacement_call["order_ref"] == "#1003"
            assert replacement_call["scope"] == {
                "line_items": [],
                "replacement_line_item_id": "102",
                "replacement_quantity": 1,
                "new_address": {"formatted": ("123 Main Street, Miami, FL 33101")},
            }
            assert replacement_call["idempotency_key"] == (
                f"support-review:{review_plan_id}:replacement"
            )

            # The reviewed destination belongs to the replacement
            # operation. It must never become an update to the
            # already-fulfilled original order.
            assert all(
                call["action"] != "update_shipping_address" for call in action_calls
            )

            messages = await client.get(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                )
            )
            assert messages.status_code == 200

            assistant_messages = [
                message for message in messages.json() if message["role"] == "assistant"
            ]

            # The complex intake produces:
            #
            # 1. clarification question
            # 2. review-ready confirmation
            # 3. durable post-approval outcome
            #
            # Do not rely on positional indexing for the semantic
            # assertions below.
            assert len(assistant_messages) == 3

            review_confirmations = [
                message["content"]
                for message in assistant_messages
                if ("ready for human review" in message["content"].lower())
            ]

            assert len(review_confirmations) == 1

            confirmation = review_confirmations[0]

            assert "Snowboard" in confirmation
            assert "Snowboard Boots" in confirmation
            assert "123 Main Street, Miami, FL 33101" in confirmation
            assert "No Shopify action has been performed" in confirmation

            expected_outcome_message = (
                "Your support request for order #1003 was approved. "
                "The requested actions have been prepared, but they "
                "have not been submitted yet."
            )

            terminal_outcomes = [
                message["content"]
                for message in assistant_messages
                if message["content"] == expected_outcome_message
            ]

            assert terminal_outcomes == [expected_outcome_message]

        from uuid import UUID

        from app.core.session import SessionLocal
        from app.domains.customer_service.repositories.chat_repository import (
            ChatRepository,
        )

        async with SessionLocal() as db:
            session = await ChatRepository(db).get_session(session_id=UUID(session_id))

            pending = (session.meta or {})["pending_support_objective"]

            assert pending["status"] == "ready_for_review"
            assert pending["objective"]["requires_clarification"] is False
            assert pending["objective"]["item_assignments"] == {
                "refund_item": "101",
                "replacement_item": "102",
            }
            assert pending["objective"]["replacement_address"] == {
                "formatted": "123 Main Street, Miami, FL 33101"
            }
            assert pending["resolution_message_id"]
            assert pending["review_plan_id"] == review_plan_id
            assert pending["review_workflow_job_id"] == review_workflow_job_id
            assert pending["review_workflow_job_status"] == "queued"
            assert pending["review_plan"]["status"] == "awaiting_human_review"
            assert pending["review_plan"]["execution_allowed"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_partial_clarification_preserves_progress_and_asks_only_remaining_fields(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    await install_verified_shopify_for_user(user.id)

    provider_calls = {
        "get_order": 0,
        "perform_order_action": 0,
    }

    async def fake_get_order(self, *, user_id, order_ref):
        provider_calls["get_order"] += 1

        return {
            "order_id": "6992274227367",
            "order_name": "#1003",
            "payload": {
                "id": "6992274227367",
                "name": "#1003",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "line_items": [
                    {
                        "id": "101",
                        "title": "Snowboard",
                        "variant_title": "158 cm",
                        "quantity": 1,
                    },
                    {
                        "id": "102",
                        "title": "Snowboard Boots",
                        "variant_title": "Size 10",
                        "quantity": 1,
                    },
                ],
            },
            "context": {},
            "summary": {},
        }

    async def forbidden_perform_order_action(self, **kwargs):
        provider_calls["perform_order_action"] += 1
        raise AssertionError("Partial clarification must not mutate Shopify")

    monkeypatch.setattr(
        ShopifyService,
        "get_order",
        fake_get_order,
    )
    monkeypatch.setattr(
        ShopifyService,
        "perform_order_action",
        forbidden_perform_order_action,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            session_id = session_response.json()["id"]

            first = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": COMPLEX_MESSAGE,
                    "client_message_id": f"initial-{uuid4()}",
                },
            )

            assert first.status_code == 200

            second = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": "Refund the Snowboard.",
                    "client_message_id": f"partial-{uuid4()}",
                },
            )

            assert second.status_code == 200, second.text
            body = second.json()

            assert body["support_intake"]["handled"] is True
            assert body["support_intake"]["continued"] is True
            assert body["support_intake"]["pending_status"] == "awaiting_customer"
            assert body["support_intake"]["requires_clarification"] is True
            assert body["support_intake"]["mutation_allowed"] is False

            objective = body["support_intake"]["objective"]

            assert objective["item_assignments"] == {
                "refund_item": "101",
                "replacement_item": None,
            }
            assert objective["replacement_address"] is None
            assert objective["missing_information"] == [
                "replacement_item",
                "replacement_address",
            ]

            assert provider_calls == {
                "get_order": 1,
                "perform_order_action": 0,
            }

            messages = await client.get(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                )
            )

            assistant_messages = [
                item for item in messages.json() if item["role"] == "assistant"
            ]

            assert len(assistant_messages) == 2

            reply = assistant_messages[-1]["content"].lower()

            assert "which item should be replaced" in reply
            assert "replacement shipping address" in reply
            assert "which item should be refunded" not in reply
            assert "no shopify action has been performed" in reply

            assert body["workflow_dispatch"]["enqueued"] == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_clarification_retry_replays_without_duplicate_resolution(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    await install_verified_shopify_for_user(user.id)

    provider_calls = {
        "get_order": 0,
        "perform_order_action": 0,
    }

    async def fake_get_order(self, *, user_id, order_ref):
        provider_calls["get_order"] += 1

        return {
            "order_id": "6992274227367",
            "order_name": "#1003",
            "payload": {
                "id": "6992274227367",
                "name": "#1003",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "line_items": [
                    {
                        "id": "101",
                        "title": "Snowboard",
                        "variant_title": "158 cm",
                        "quantity": 1,
                    },
                    {
                        "id": "102",
                        "title": "Snowboard Boots",
                        "variant_title": "Size 10",
                        "quantity": 1,
                    },
                ],
            },
            "context": {},
            "summary": {},
        }

    async def forbidden_perform_order_action(self, **kwargs):
        provider_calls["perform_order_action"] += 1
        raise AssertionError("Clarification replay must not mutate Shopify")

    monkeypatch.setattr(
        ShopifyService,
        "get_order",
        fake_get_order,
    )
    monkeypatch.setattr(
        ShopifyService,
        "perform_order_action",
        forbidden_perform_order_action,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            session_id = session_response.json()["id"]

            url = (
                f"/customer-service/chat/public/{public_key}"
                f"/sessions/{session_id}/messages"
            )

            initial = await client.post(
                url,
                json={
                    "content": COMPLEX_MESSAGE,
                    "client_message_id": f"initial-{uuid4()}",
                },
            )

            assert initial.status_code == 200

            clarification_client_id = f"clarification-replay-{uuid4()}"
            clarification_payload = {
                "content": CLARIFICATION_MESSAGE,
                "client_message_id": clarification_client_id,
            }

            first = await client.post(
                url,
                json=clarification_payload,
            )
            second = await client.post(
                url,
                json=clarification_payload,
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            first_body = first.json()
            second_body = second.json()

            assert first_body["idempotent_replay"] is False
            assert second_body["idempotent_replay"] is True

            assert second_body["id"] == first_body["id"]
            assert second_body["event_id"] == first_body["event_id"]
            assert second_body["workflow_dispatch"] == first_body["workflow_dispatch"]
            assert second_body["support_intake"] == first_body["support_intake"]
            assert first_body["support_intake"]["review_plan_id"] is not None
            assert (
                second_body["support_intake"]["review_plan_id"]
                == first_body["support_intake"]["review_plan_id"]
            )
            assert (
                second_body["support_intake"]["review_plan"]
                == first_body["support_intake"]["review_plan"]
            )
            assert first_body["support_intake"]["review_workflow_job_id"] is not None
            assert (
                second_body["support_intake"]["review_workflow_job_id"]
                == first_body["support_intake"]["review_workflow_job_id"]
            )
            # A live worker may claim or even complete the review
            # workflow between the two idempotent requests. The durable
            # contract is stable job identity and a valid non-failure
            # lifecycle state, not an exact queue snapshot.
            review_job_active_statuses = {
                "queued",
                "running",
                "succeeded",
            }

            assert (
                first_body["support_intake"]["review_workflow_job_status"]
                in review_job_active_statuses
            )
            assert (
                second_body["support_intake"]["review_workflow_job_status"]
                in review_job_active_statuses
            )

            assert first_body["support_intake"]["pending_status"] == "ready_for_review"

            assert provider_calls == {
                "get_order": 1,
                "perform_order_action": 0,
            }

            messages = await client.get(url)
            assert messages.status_code == 200

            customer_clarifications = [
                item
                for item in messages.json()
                if item["role"] == "customer"
                and item["content"] == CLARIFICATION_MESSAGE
            ]

            resolution_messages = [
                item
                for item in messages.json()
                if item["role"] == "assistant"
                and "ready for human review" in item["content"].lower()
            ]

            assert len(customer_clarifications) == 1
            assert len(resolution_messages) == 1

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            matching_jobs = [
                job
                for job in jobs.json()
                if job["job_type"] == "workflow.run"
                and job["payload"].get("message") == CLARIFICATION_MESSAGE
            ]

            assert matching_jobs == []

            review_plan_id = first_body["support_intake"]["review_plan_id"]
            review_workflow_job_id = first_body["support_intake"][
                "review_workflow_job_id"
            ]

            review_jobs = [
                job
                for job in jobs.json()
                if (
                    job["job_type"] == "workflow.run"
                    and job["payload"]
                    .get("extras", {})
                    .get("support_review", {})
                    .get("review_plan_id")
                    == review_plan_id
                )
            ]

            assert len(review_jobs) == 1
            assert review_jobs[0]["id"] == review_workflow_job_id
            assert review_jobs[0]["status"] in review_job_active_statuses
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_whole_refund_missing_order_resumes_into_durable_review_workflow(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    await install_verified_shopify_for_user(user.id)

    provider_calls = {
        "get_order": 0,
        "perform_order_action": 0,
    }

    async def fake_get_order(self, *, user_id, order_ref):
        provider_calls["get_order"] += 1

        assert user_id == user.id
        assert order_ref == "1001"

        return {
            "order_id": "6992274227001",
            "order_name": "#1001",
            "payload": {
                "id": "6992274227001",
                "name": "#1001",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "total_price": "99.00",
                "currency": "USD",
                "line_items": [
                    {
                        "id": "101",
                        "title": "Snowboard",
                        "variant_title": "158 cm",
                        "quantity": 1,
                    },
                ],
            },
            "context": {},
            "summary": {},
        }

    action_calls = []

    async def fake_perform_order_action(self, **kwargs):
        provider_calls["perform_order_action"] += 1
        action_calls.append(kwargs)

        assert kwargs["user_id"] == user.id
        assert kwargs["order_ref"] == "#1001"
        assert kwargs["action"] == "refund"

        return {
            "scope": {},
            "action": "refund",
            "status": "prepared",
            "message": ("Real order found. Refund is prepared but not submitted yet."),
            "payload": {
                "scope": {},
                "amount": kwargs.get("amount"),
                "reason": kwargs.get("reason"),
                "status": "prepared",
                "message": (
                    "Real order found. Refund is prepared but not submitted yet."
                ),
                "order_id": "6992274227001",
                "order_name": "#1001",
                "financial_status": "paid",
            },
            "order_id": "6992274227001",
            "order_name": "#1001",
            "idempotency_key": kwargs.get("idempotency_key"),
        }

    monkeypatch.setattr(
        ShopifyService,
        "get_order",
        fake_get_order,
    )
    monkeypatch.setattr(
        ShopifyService,
        "perform_order_action",
        fake_perform_order_action,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            assert settings.status_code == 200

            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200

            session_id = session_response.json()["id"]

            # First turn: actionable objective, but no order reference.
            first = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": "I want a refund.",
                    "client_message_id": f"whole-refund-{uuid4()}",
                },
            )

            assert first.status_code == 200, first.text

            first_body = first.json()

            assert first_body["support_intake"]["handled"] is True
            assert (
                first_body["support_intake"]["pending_status"] == "awaiting_order_ref"
            )
            assert first_body["support_intake"]["objective"]["requested_actions"] == [
                "whole_refund"
            ]
            assert first_body["support_intake"]["objective"]["order_ref"] is None
            assert first_body["workflow_dispatch"]["enqueued"] == []

            # We must not query or mutate Shopify before the customer
            # provides the missing order reference.
            assert provider_calls == {
                "get_order": 0,
                "perform_order_action": 0,
            }

            # Second turn: only supply the missing fact. The persisted
            # WHOLE_REFUND objective must remain the source of truth.
            second = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": "#1001",
                    "client_message_id": f"order-ref-{uuid4()}",
                },
            )

            assert second.status_code == 200, second.text

            second_body = second.json()
            support = second_body["support_intake"]

            assert support["handled"] is True
            assert support["continued"] is True
            assert support["requires_clarification"] is False
            assert support["mutation_allowed"] is False
            assert support["pending_status"] == "ready_for_review"

            assert support["objective"]["order_ref"] == "1001"
            assert support["objective"]["requested_actions"] == ["whole_refund"]
            assert support["objective"]["requires_clarification"] is False

            review_plan_id = support["review_plan_id"]

            assert review_plan_id
            assert support["review_workflow_job_id"]
            assert support["review_workflow_job_status"] == "queued"

            review_plan = support["review_plan"]

            assert review_plan["status"] == "awaiting_human_review"
            assert review_plan["approval_required"] is True
            assert review_plan["execution_allowed"] is False
            assert review_plan["order_ref"] == "#1001"

            assert [
                operation["operation_type"] for operation in review_plan["operations"]
            ] == ["whole_refund"]

            assert provider_calls == {
                "get_order": 1,
                "perform_order_action": 0,
            }

            # Verify the actual queued durable workflow, not only the
            # serialized review plan returned by the ingress endpoint.
            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            review_jobs = [
                job
                for job in jobs.json()
                if (
                    job["job_type"] == "workflow.run"
                    and job["payload"]
                    .get("extras", {})
                    .get("support_review", {})
                    .get("review_plan_id")
                    == review_plan_id
                )
            ]

            assert len(review_jobs) == 1

            workflow = review_jobs[0]["payload"]["workflow"]

            approval = next(
                node for node in workflow["nodes"] if node["id"] == "approval"
            )
            whole_refund = next(
                node
                for node in workflow["nodes"]
                if node["id"] == "prepare_whole_refund"
            )

            assert approval["data"]["nodeType"] == "human.approval"

            assert whole_refund["data"]["nodeType"] == "capability.invoke"
            assert (
                whole_refund["data"]["config"]["capability_id"]
                == "ecommerce.orders.action"
            )

            refund_payload = whole_refund["data"]["config"]["payload"]

            assert refund_payload["action"] == "refund"
            assert refund_payload["order_ref"] == "#1001"
            assert refund_payload["amount"] is None
            assert refund_payload["scope"] is None
            assert refund_payload["idempotency_key"] == (
                f"support-review:{review_plan_id}:whole-refund"
            )

            assert {
                "source": "route_approval",
                "target": "prepare_whole_refund",
                "condition": "approved",
            } in workflow["edges"]

            # Outcome delivery is part of the same durable workflow.
            assert review_jobs[0]["payload"]["extras"]["session_id"] == session_id

            assert {
                "source": "prepare_whole_refund",
                "target": "join_preparation_results",
            } in workflow["edges"]

            assert {
                "source": "join_preparation_results",
                "target": "project_approved_outcome",
            } in workflow["edges"]

            assert {
                "source": "project_approved_outcome",
                "target": "record_approved_outcome",
            } in workflow["edges"]

            assert {
                "source": "record_approved_outcome",
                "target": "reply_approved_outcome",
            } in workflow["edges"]

            assert {
                "source": "reply_approved_outcome",
                "target": "approved_response",
            } in workflow["edges"]

            # ---------------------------------------------------------
            # Execute the durable workflow up to its approval boundary.
            # ---------------------------------------------------------

            from uuid import UUID

            from app.core.session import SessionLocal
            from app.workflow_operations.waits.service import (
                WorkflowWaitService,
            )

            async with SessionLocal() as worker_db:
                started_job = await JobWorker(
                    worker_db,
                    worker_id=("whole-refund-outcome-start"),
                ).run_once(job_id=UUID(support["review_workflow_job_id"]))

                assert started_job is not None
                assert started_job.status == "succeeded", {
                    "error": started_job.error_message,
                    "result": started_job.result,
                }
                assert started_job.result["meta"]["status"] == "paused"

                workflow_run_id = started_job.result["meta"]["workflow_run_id"]

                waits = await WorkflowWaitService(worker_db).list_for_user(
                    user_id=user.id,
                    status="waiting",
                    workflow_run_id=workflow_run_id,
                )

                approval_waits = [
                    wait
                    for wait in waits
                    if (wait.wait_type == "approval" and wait.node_id == "approval")
                ]

                assert len(approval_waits) == 1
                approval_wait = approval_waits[0]

                # Provider action is still blocked before approval.
                assert provider_calls == {
                    "get_order": 1,
                    "perform_order_action": 0,
                }
                assert action_calls == []

                before_approval_messages = await client.get(
                    (
                        f"/customer-service/chat/public/"
                        f"{public_key}/sessions/"
                        f"{session_id}/messages"
                    )
                )
                assert before_approval_messages.status_code == 200

                expected_outcome_message = (
                    "Your refund request for order #1001 "
                    "was approved. The refund has been "
                    "prepared, but it has not been "
                    "submitted yet."
                )

                assert [
                    item
                    for item in before_approval_messages.json()
                    if (
                        item["role"] == "assistant"
                        and item["content"] == expected_outcome_message
                    )
                ] == []

                # -----------------------------------------------------
                # Human approval resolves the wait and creates a
                # workflow.resume job.
                # -----------------------------------------------------

                approval_response = await client.post(
                    (f"/workflow-waits/{approval_wait.id}/approve")
                )

                assert approval_response.status_code == 200, approval_response.text

                approval_body = approval_response.json()

                assert approval_body["approved"] is True
                assert approval_body["status"] == "resolved"
                assert approval_body["workflow_run_id"] == workflow_run_id
                assert approval_body["resume_job_id"]

                resumed_job = await JobWorker(
                    worker_db,
                    worker_id=("whole-refund-outcome-resume"),
                ).run_once(job_id=UUID(approval_body["resume_job_id"]))

                assert resumed_job is not None
                assert resumed_job.status == "succeeded", {
                    "error": resumed_job.error_message,
                    "result": resumed_job.result,
                }
                assert resumed_job.result["meta"]["status"] == "ok"

                # Exactly one provider preparation occurs.
                assert provider_calls == {
                    "get_order": 1,
                    "perform_order_action": 1,
                }
                assert len(action_calls) == 1

                action_call = action_calls[0]

                assert action_call["action"] == "refund"
                assert action_call["order_ref"] == "#1001"
                assert action_call["amount"] is None
                assert action_call["scope"] is None
                assert action_call["idempotency_key"] == (
                    f"support-review:{review_plan_id}:whole-refund"
                )

                # -----------------------------------------------------
                # Provider success means PREPARED here, not submitted
                # or completed. Verify the domain projection survived
                # through the runtime result.
                # -----------------------------------------------------

                final_state = resumed_job.result["meta"]["final_state"]

                support_outcome = final_state["vars"]["support_outcome"]

                assert support_outcome["decision"] == "approved"
                assert support_outcome["order_ref"] == "#1001"

                assert len(support_outcome["operations"]) == 1

                operation_outcome = support_outcome["operations"][0]

                assert operation_outcome["operation_type"] == "whole_refund"
                assert operation_outcome["status"] == "prepared"
                assert operation_outcome["prepared"] is True
                assert operation_outcome["submitted"] is False
                assert operation_outcome["completed"] is False

                assert support_outcome["customer_message"] == expected_outcome_message

            # ---------------------------------------------------------
            # Customer sees exactly one terminal outcome message.
            # ---------------------------------------------------------

            messages_after_approval = await client.get(
                (
                    f"/customer-service/chat/public/"
                    f"{public_key}/sessions/"
                    f"{session_id}/messages"
                )
            )

            assert messages_after_approval.status_code == 200

            outcome_messages = [
                item
                for item in messages_after_approval.json()
                if (
                    item["role"] == "assistant"
                    and item["content"] == expected_outcome_message
                )
            ]

            assert len(outcome_messages) == 1

        # Verify the same objective lifecycle was durably persisted on
        # the chat session.
        from uuid import UUID

        from app.core.session import SessionLocal
        from app.domains.customer_service.repositories.chat_repository import (
            ChatRepository,
        )

        async with SessionLocal() as db:
            persisted_session = await ChatRepository(db).get_session(
                session_id=UUID(session_id)
            )

            pending = (persisted_session.meta or {})["pending_support_objective"]

            assert pending["status"] == "ready_for_review"
            assert pending["objective"]["order_ref"] == "1001"
            assert pending["objective"]["requested_actions"] == ["whole_refund"]
            assert pending["review_plan_id"] == review_plan_id
            assert (
                pending["review_workflow_job_id"] == support["review_workflow_job_id"]
            )
            assert pending["review_workflow_job_status"] == "queued"
            assert [
                operation["operation_type"]
                for operation in pending["review_plan"]["operations"]
            ] == ["whole_refund"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_whole_refund_rejected_resumes_into_customer_safe_rejected_outcome(
    monkeypatch,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    await install_verified_shopify_for_user(user.id)

    provider_calls = {
        "get_order": 0,
        "perform_order_action": 0,
    }

    async def fake_get_order(self, *, user_id, order_ref):
        provider_calls["get_order"] += 1

        assert user_id == user.id
        assert order_ref == "1001"

        return {
            "order_id": "6992274227001",
            "order_name": "#1001",
            "payload": {
                "id": "6992274227001",
                "name": "#1001",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "total_price": "99.00",
                "currency": "USD",
                "line_items": [
                    {
                        "id": "101",
                        "title": "Snowboard",
                        "variant_title": "158 cm",
                        "quantity": 1,
                    },
                ],
            },
            "context": {},
            "summary": {},
        }

    action_calls = []

    async def fake_perform_order_action(self, **kwargs):
        provider_calls["perform_order_action"] += 1
        action_calls.append(kwargs)

        assert kwargs["user_id"] == user.id
        assert kwargs["order_ref"] == "#1001"
        assert kwargs["action"] == "refund"

        return {
            "scope": {},
            "action": "refund",
            "status": "prepared",
            "message": ("Real order found. Refund is prepared but not submitted yet."),
            "payload": {
                "scope": {},
                "amount": kwargs.get("amount"),
                "reason": kwargs.get("reason"),
                "status": "prepared",
                "message": (
                    "Real order found. Refund is prepared but not submitted yet."
                ),
                "order_id": "6992274227001",
                "order_name": "#1001",
                "financial_status": "paid",
            },
            "order_id": "6992274227001",
            "order_name": "#1001",
            "idempotency_key": kwargs.get("idempotency_key"),
        }

    monkeypatch.setattr(
        ShopifyService,
        "get_order",
        fake_get_order,
    )
    monkeypatch.setattr(
        ShopifyService,
        "perform_order_action",
        fake_perform_order_action,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            assert settings.status_code == 200

            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200

            session_id = session_response.json()["id"]

            # First turn: actionable objective, but no order reference.
            first = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": "I want a refund.",
                    "client_message_id": f"whole-refund-{uuid4()}",
                },
            )

            assert first.status_code == 200, first.text

            first_body = first.json()

            assert first_body["support_intake"]["handled"] is True
            assert (
                first_body["support_intake"]["pending_status"] == "awaiting_order_ref"
            )
            assert first_body["support_intake"]["objective"]["requested_actions"] == [
                "whole_refund"
            ]
            assert first_body["support_intake"]["objective"]["order_ref"] is None
            assert first_body["workflow_dispatch"]["enqueued"] == []

            # We must not query or mutate Shopify before the customer
            # provides the missing order reference.
            assert provider_calls == {
                "get_order": 0,
                "perform_order_action": 0,
            }

            # Second turn: only supply the missing fact. The persisted
            # WHOLE_REFUND objective must remain the source of truth.
            second = await client.post(
                (
                    f"/customer-service/chat/public/{public_key}"
                    f"/sessions/{session_id}/messages"
                ),
                json={
                    "content": "#1001",
                    "client_message_id": f"order-ref-{uuid4()}",
                },
            )

            assert second.status_code == 200, second.text

            second_body = second.json()
            support = second_body["support_intake"]

            assert support["handled"] is True
            assert support["continued"] is True
            assert support["requires_clarification"] is False
            assert support["mutation_allowed"] is False
            assert support["pending_status"] == "ready_for_review"

            assert support["objective"]["order_ref"] == "1001"
            assert support["objective"]["requested_actions"] == ["whole_refund"]
            assert support["objective"]["requires_clarification"] is False

            review_plan_id = support["review_plan_id"]

            assert review_plan_id
            assert support["review_workflow_job_id"]
            assert support["review_workflow_job_status"] == "queued"

            review_plan = support["review_plan"]

            assert review_plan["status"] == "awaiting_human_review"
            assert review_plan["approval_required"] is True
            assert review_plan["execution_allowed"] is False
            assert review_plan["order_ref"] == "#1001"

            assert [
                operation["operation_type"] for operation in review_plan["operations"]
            ] == ["whole_refund"]

            assert provider_calls == {
                "get_order": 1,
                "perform_order_action": 0,
            }

            # Verify the actual queued durable workflow, not only the
            # serialized review plan returned by the ingress endpoint.
            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            review_jobs = [
                job
                for job in jobs.json()
                if (
                    job["job_type"] == "workflow.run"
                    and job["payload"]
                    .get("extras", {})
                    .get("support_review", {})
                    .get("review_plan_id")
                    == review_plan_id
                )
            ]

            assert len(review_jobs) == 1

            workflow = review_jobs[0]["payload"]["workflow"]

            approval = next(
                node for node in workflow["nodes"] if node["id"] == "approval"
            )
            whole_refund = next(
                node
                for node in workflow["nodes"]
                if node["id"] == "prepare_whole_refund"
            )

            assert approval["data"]["nodeType"] == "human.approval"

            assert whole_refund["data"]["nodeType"] == "capability.invoke"
            assert (
                whole_refund["data"]["config"]["capability_id"]
                == "ecommerce.orders.action"
            )

            refund_payload = whole_refund["data"]["config"]["payload"]

            assert refund_payload["action"] == "refund"
            assert refund_payload["order_ref"] == "#1001"
            assert refund_payload["amount"] is None
            assert refund_payload["scope"] is None
            assert refund_payload["idempotency_key"] == (
                f"support-review:{review_plan_id}:whole-refund"
            )

            assert {
                "source": "route_approval",
                "target": "prepare_whole_refund",
                "condition": "approved",
            } in workflow["edges"]

            assert {
                "source": "route_approval",
                "target": "set_rejected_result",
                "condition": "rejected",
            } in workflow["edges"]

            # Outcome delivery is part of the same durable workflow.
            assert review_jobs[0]["payload"]["extras"]["session_id"] == session_id

            assert {
                "source": "prepare_whole_refund",
                "target": "join_preparation_results",
            } in workflow["edges"]

            assert {
                "source": "join_preparation_results",
                "target": "project_approved_outcome",
            } in workflow["edges"]

            assert {
                "source": "project_approved_outcome",
                "target": "record_approved_outcome",
            } in workflow["edges"]

            assert {
                "source": "record_approved_outcome",
                "target": "reply_approved_outcome",
            } in workflow["edges"]

            assert {
                "source": "reply_approved_outcome",
                "target": "approved_response",
            } in workflow["edges"]

            assert {
                "source": "set_rejected_result",
                "target": "project_rejected_outcome",
            } in workflow["edges"]

            assert {
                "source": "project_rejected_outcome",
                "target": "record_rejected_outcome",
            } in workflow["edges"]

            assert {
                "source": "record_rejected_outcome",
                "target": "reply_rejected_outcome",
            } in workflow["edges"]

            assert {
                "source": "reply_rejected_outcome",
                "target": "rejected_response",
            } in workflow["edges"]

            # ---------------------------------------------------------
            # Execute the durable workflow up to its approval boundary.
            # ---------------------------------------------------------

            from uuid import UUID

            from app.core.session import SessionLocal
            from app.workflow_operations.waits.service import (
                WorkflowWaitService,
            )

            async with SessionLocal() as worker_db:
                started_job = await JobWorker(
                    worker_db,
                    worker_id=("whole-refund-rejected-start"),
                ).run_once(job_id=UUID(support["review_workflow_job_id"]))

                assert started_job is not None
                assert started_job.status == "succeeded", {
                    "error": started_job.error_message,
                    "result": started_job.result,
                }
                assert started_job.result["meta"]["status"] == "paused"

                workflow_run_id = started_job.result["meta"]["workflow_run_id"]

                waits = await WorkflowWaitService(worker_db).list_for_user(
                    user_id=user.id,
                    status="waiting",
                    workflow_run_id=workflow_run_id,
                )

                approval_waits = [
                    wait
                    for wait in waits
                    if (wait.wait_type == "approval" and wait.node_id == "approval")
                ]

                assert len(approval_waits) == 1
                approval_wait = approval_waits[0]

                # Provider action is still blocked before review resolution.
                assert provider_calls == {
                    "get_order": 1,
                    "perform_order_action": 0,
                }
                assert action_calls == []

                before_rejection_messages = await client.get(
                    (
                        f"/customer-service/chat/public/"
                        f"{public_key}/sessions/"
                        f"{session_id}/messages"
                    )
                )
                assert before_rejection_messages.status_code == 200

                expected_outcome_message = (
                    "Your refund request for order #1001 "
                    "was not approved. No refund was submitted."
                )

                assert [
                    item
                    for item in before_rejection_messages.json()
                    if (
                        item["role"] == "assistant"
                        and item["content"] == expected_outcome_message
                    )
                ] == []

                # -----------------------------------------------------
                # Human rejection resolves the wait and creates a
                # workflow.resume job.
                # -----------------------------------------------------

                rejection_response = await client.post(
                    (f"/workflow-waits/{approval_wait.id}/reject")
                )

                assert rejection_response.status_code == 200, rejection_response.text

                rejection_body = rejection_response.json()

                assert rejection_body["approved"] is False
                assert rejection_body["status"] == "resolved"
                assert rejection_body["workflow_run_id"] == workflow_run_id
                assert rejection_body["resume_job_id"]

                resumed_job = await JobWorker(
                    worker_db,
                    worker_id=("whole-refund-rejected-resume"),
                ).run_once(job_id=UUID(rejection_body["resume_job_id"]))

                assert resumed_job is not None
                assert resumed_job.status == "succeeded", {
                    "error": resumed_job.error_message,
                    "result": resumed_job.result,
                }
                assert resumed_job.result["meta"]["status"] == "ok"

                # Human rejection must terminate the mutation branch.
                #
                # No ecommerce.orders.action capability execution is
                # allowed after rejection.
                assert provider_calls == {
                    "get_order": 1,
                    "perform_order_action": 0,
                }
                assert action_calls == []

                # -----------------------------------------------------
                # Verify the rejected domain outcome survived through
                # the durable resume path.
                # -----------------------------------------------------

                final_state = resumed_job.result["meta"]["final_state"]

                support_outcome = final_state["vars"]["support_outcome"]

                assert support_outcome["decision"] == "rejected"
                assert support_outcome["order_ref"] == "#1001"

                # The rejected outcome preserves what the customer
                # requested, but explicitly records that the operation
                # was rejected and never executed.
                assert len(support_outcome["operations"]) == 1

                rejected_operation = support_outcome["operations"][0]

                assert rejected_operation["operation_type"] == "whole_refund"
                assert rejected_operation["status"] == "rejected"
                assert rejected_operation["prepared"] is False
                assert rejected_operation["submitted"] is False
                assert rejected_operation["completed"] is False
                assert rejected_operation["provider_result"] == {}

                assert support_outcome["customer_message"] == expected_outcome_message

            # ---------------------------------------------------------
            # Customer sees exactly one terminal outcome message.
            # ---------------------------------------------------------

            messages_after_rejection = await client.get(
                (
                    f"/customer-service/chat/public/"
                    f"{public_key}/sessions/"
                    f"{session_id}/messages"
                )
            )

            assert messages_after_rejection.status_code == 200

            outcome_messages = [
                item
                for item in messages_after_rejection.json()
                if (
                    item["role"] == "assistant"
                    and item["content"] == expected_outcome_message
                )
            ]

            assert len(outcome_messages) == 1

        # Verify the same objective lifecycle was durably persisted on
        # the chat session.
        from uuid import UUID

        from app.core.session import SessionLocal
        from app.domains.customer_service.repositories.chat_repository import (
            ChatRepository,
        )

        async with SessionLocal() as db:
            persisted_session = await ChatRepository(db).get_session(
                session_id=UUID(session_id)
            )

            pending = (persisted_session.meta or {})["pending_support_objective"]

            assert pending["status"] == "ready_for_review"
            assert pending["objective"]["order_ref"] == "1001"
            assert pending["objective"]["requested_actions"] == ["whole_refund"]
            assert pending["review_plan_id"] == review_plan_id
            assert (
                pending["review_workflow_job_id"] == support["review_workflow_job_id"]
            )
            assert pending["review_workflow_job_status"] == "queued"
            assert [
                operation["operation_type"]
                for operation in pending["review_plan"]["operations"]
            ] == ["whole_refund"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
