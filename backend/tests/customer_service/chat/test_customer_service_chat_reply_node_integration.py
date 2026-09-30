from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.api.auth import get_current_user
from app.runtime.engine.context import RuntimeContext
from app.domains.customer_service.runtime.nodes.customer_chat import (
    CustomerChatReplyConfig,
    CustomerChatReplyNode,
)
from app.domains.customer_service.realtime.publisher import (
    CustomerServiceRealtimePublisher,
)
from app.domains.customer_service.services.sla import SLAService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chat-reply-integration@example.com"


class DummyRequest:
    def __init__(self):
        self.state = type("State", (), {"tools": None})()
        self.app = app


@pytest.mark.asyncio
async def test_reply_customer_chat_node_writes_chat_and_inbox_rows():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

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

        async with SessionLocal() as db:
            ctx = RuntimeContext(
                request=DummyRequest(),
                user_id=str(user.id),
                thread_id=session["conversation_id"],
                db=db,
                extras={},
            )

            result = await CustomerChatReplyNode().run(
                ctx,
                state={"vars": {}, "last": "Hello from workflow"},
                config=CustomerChatReplyConfig(
                    session_id_from="config",
                    session_id=session["id"],
                    message_from="last",
                ),
            )

            assert result["output"]["role"] == "assistant"
            assert result["output"]["content"] == "Hello from workflow"
            assert result["output"]["session_id"] == session["id"]
            assert result["output"]["conversation_id"] == session["conversation_id"]
            assert result["output"]["inbox_message_id"]
            assert result["patch"]["vars"]["customer_chat_reply_sent"] is True

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            chat_messages = await client.get(
                f"/customer-service/chat/public/{public_key}/sessions/{session['id']}/messages"
            )
            assert chat_messages.status_code == 200
            assert any(
                msg["role"] == "assistant" and msg["content"] == "Hello from workflow"
                for msg in chat_messages.json()
            )

            detail = await client.get(
                f"/customer-service/conversations/{session['conversation_id']}"
            )
            assert detail.status_code == 200
            assert any(
                msg["sender_type"] == "ai"
                and msg["body"] == "Hello from workflow"
                and msg["meta"]["source"] == "customer_chat"
                for msg in detail.json()["messages"]
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_reply_customer_chat_same_runtime_key_creates_exactly_one_chat_and_inbox_message(monkeypatch):
    """
    Harsh durable-side-effect case:

    The same reply.customer_chat logical execution runs twice with the
    same runtime idempotency key.

    This simulates an ambiguous worker retry after the first attempt may
    already have persisted its customer-visible side effect.

    Expected:
      - the CustomerChatMessage is created once
      - the Inbox ConversationMessage mirror is created once
      - both executions resolve to the same persisted identities
      - Inbox source identity points at the persisted chat message
    """
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    message_text = (
        "Your refund request for order #1001 was approved. "
        "The refund has been prepared, but it has not been submitted yet."
    )

    runtime_idempotency_key = (
        f"test:reply-customer-chat:exactly-once:{uuid4()}"
    )

    try:
        # ------------------------------------------------------------
        # Create a real customer chat session + Inbox bridge.
        # ------------------------------------------------------------
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get(
                "/customer-service/chat/widget/settings"
            )
            assert settings.status_code == 200

            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/"
                f"{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )

            assert session_response.status_code == 200
            session = session_response.json()

        # ------------------------------------------------------------
        # Count secondary Inbox effects caused by this logical reply.
        #
        # Patch only after the real chat session / conversation / ticket
        # have been created so setup work is not included.
        # ------------------------------------------------------------
        secondary_effects = {
            "realtime_publish": 0,
            "sla_first_response": 0,
        }

        async def fake_publish_message_created(
            _publisher,
            **_kwargs,
        ):
            secondary_effects["realtime_publish"] += 1

        async def fake_resolve_first_response_targets(
            _service,
            *,
            ticket_id,
        ):
            assert ticket_id is not None
            secondary_effects["sla_first_response"] += 1
            return []

        monkeypatch.setattr(
            CustomerServiceRealtimePublisher,
            "publish_message_created",
            fake_publish_message_created,
        )

        monkeypatch.setattr(
            SLAService,
            "resolve_first_response_targets",
            fake_resolve_first_response_targets,
        )

        # ------------------------------------------------------------
        # Execute the SAME logical side effect twice.
        #
        # Same:
        #   - chat session
        #   - message
        #   - runtime idempotency key
        #
        # This is the retry boundary we care about.
        # ------------------------------------------------------------
        async with SessionLocal() as db:
            ctx = RuntimeContext(
                request=DummyRequest(),
                user_id=str(user.id),
                thread_id=session["conversation_id"],
                db=db,
                extras={},
            )

            ctx.node_data = {
                "_runtime": {
                    "idempotency_key": runtime_idempotency_key,
                }
            }

            config = CustomerChatReplyConfig(
                session_id_from="config",
                session_id=session["id"],
                message_from="last",
            )

            state = {
                "vars": {},
                "last": message_text,
            }

            first = await CustomerChatReplyNode().run(
                ctx,
                state=state,
                config=config,
            )

            second = await CustomerChatReplyNode().run(
                ctx,
                state=state,
                config=config,
            )

            # The node should report the same logical runtime identity.
            assert (
                first["output"]["idempotency_key"]
                == runtime_idempotency_key
            )
            assert (
                second["output"]["idempotency_key"]
                == runtime_idempotency_key
            )

            # The Inbox mirror must resolve to the same persisted row.
            assert (
                first["output"]["inbox_message_id"]
                == second["output"]["inbox_message_id"]
            )

            assert (
                first["output"]["session_id"]
                == second["output"]["session_id"]
                == session["id"]
            )

            assert (
                first["output"]["conversation_id"]
                == second["output"]["conversation_id"]
                == session["conversation_id"]
            )

            # The first durable Inbox creation performs its secondary
            # effects. The retry resolves to the existing row and must
            # return before repeating either effect.
            assert secondary_effects == {
                "realtime_publish": 1,
                "sla_first_response": 1,
            }

        # ------------------------------------------------------------
        # Public Chat must contain exactly ONE terminal AI message.
        # ------------------------------------------------------------
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            chat_response = await client.get(
                f"/customer-service/chat/public/"
                f"{public_key}/sessions/"
                f"{session['id']}/messages"
            )

            assert chat_response.status_code == 200

            chat_matches = [
                message
                for message in chat_response.json()
                if message["role"] == "assistant"
                and message["content"] == message_text
            ]

            assert len(chat_matches) == 1

            chat_message = chat_matches[0]

            # --------------------------------------------------------
            # Inbox must also contain exactly ONE mirrored message.
            # --------------------------------------------------------
            detail_response = await client.get(
                f"/customer-service/conversations/"
                f"{session['conversation_id']}"
            )

            assert detail_response.status_code == 200

            inbox_matches = [
                message
                for message
                in detail_response.json()["messages"]
                if message["sender_type"] == "ai"
                and message["body"] == message_text
                and message["meta"]["source"]
                == "customer_chat"
            ]

            assert len(inbox_matches) == 1

            inbox_message = inbox_matches[0]

            # First-class durable source identity.
            assert (
                inbox_message["source_type"]
                == "customer_chat"
            )

            assert (
                inbox_message["source_message_id"]
                == chat_message["id"]
            )

            # JSON metadata remains useful for traceability,
            # but is not the uniqueness mechanism.
            assert (
                inbox_message["meta"]["chat_message_id"]
                == chat_message["id"]
            )

            # The id returned by both executions is the one persisted
            # in the Inbox.
            assert (
                first["output"]["inbox_message_id"]
                == inbox_message["id"]
            )

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )



@pytest.mark.asyncio
async def test_conversation_message_source_identity_requires_both_fields():
    from app.domains.customer_service.repositories.conversations import (
        ConversationRepository,
    )
    from app.domains.customer_service.schemas.conversations import (
        ConversationMessageCreate,
        SenderType,
    )

    async with SessionLocal() as db:
        repo = ConversationRepository(db)

        with pytest.raises(
            ValueError,
            match=(
                "source_type and source_message_id "
                "must be provided together"
            ),
        ):
            await repo.add_message_with_result(
                conversation_id=uuid4(),
                message=ConversationMessageCreate(
                    sender_type=SenderType.AI,
                    body="invalid partial source identity",
                    source_type="customer_chat",
                    source_message_id=None,
                ),
                commit=False,
            )




@pytest.mark.asyncio
async def test_conversation_message_source_identity_rejects_blank_source_type():
    from app.domains.customer_service.repositories.conversations import (
        ConversationRepository,
    )
    from app.domains.customer_service.schemas.conversations import (
        ConversationMessageCreate,
        SenderType,
    )

    async with SessionLocal() as db:
        repo = ConversationRepository(db)

        with pytest.raises(
            ValueError,
            match=(
                "source_type and source_message_id "
                "must be provided together"
            ),
        ):
            await repo.add_message_with_result(
                conversation_id=uuid4(),
                message=ConversationMessageCreate(
                    sender_type=SenderType.AI,
                    body="invalid blank source identity",
                    source_type="   ",
                    source_message_id=uuid4(),
                ),
                commit=False,
            )

