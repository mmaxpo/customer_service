from __future__ import annotations

from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from app.domains.customer_service.integrations.omnichannel.errors import (
    OmnichannelProviderPermanentError,
    OmnichannelProviderTransientError,
)
from app.domains.customer_service.integrations.omnichannel.protocol import (
    FetchedInboundMedia,
)
from app.domains.customer_service.workflows.omnichannel_job_types import (
    OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
)


def _payload(
    *,
    user_id,
    conversation_id,
    message_id,
    provider_media_id="media-1",
):
    return {
        "user_id": str(user_id),
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "channel": "worker-media-test",
        "external_account_id": "account-1",
        "external_message_id": "message-1",
        "provider_media_id": provider_media_id,
        "media": {
            "provider_media_id": provider_media_id,
            "filename": "photo.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 4,
            "metadata": {
                "source": "test",
            },
        },
    }


class FakeJob:
    def __init__(self, user_id):
        self.user_id = user_id
        self.max_attempts = 3
        self.attempts = 1


class FakeDb:
    def __init__(self):
        self.executions = []

    async def execute(
        self,
        statement,
        params=None,
    ):
        self.executions.append(
            (
                str(statement),
                dict(params or {}),
            )
        )
        return None


class FakeCtx:
    def __init__(self, user_id):
        self.db = FakeDb()
        self.job = FakeJob(user_id)
        self.worker_id = "media-worker-test"
        self.retryable = True


@pytest.mark.asyncio
async def test_inbound_media_worker_materializes_once(
    monkeypatch,
):
    from app.domains.customer_service.workflows import (
        omnichannel_jobs as module,
    )

    user_id = uuid4()
    conversation_id = uuid4()
    message_id = uuid4()
    link_id = uuid4()

    calls = {
        "fetch": 0,
        "store": 0,
        "link": 0,
    }

    class FakeRepo:
        def __init__(self, db):
            pass

        async def get_external_media(self, **kwargs):
            return None

        async def get_external_message(self, **kwargs):
            return SimpleNamespace(
                conversation_id=conversation_id,
                message_id=message_id,
            )

        async def get_connection(self, **kwargs):
            return SimpleNamespace(
                channel="worker-media-test",
                external_account_id="account-1",
                config={"provider_setting": "opaque"},
            )

        async def link_external_media(self, **kwargs):
            calls["link"] += 1
            assert kwargs["attachment_id"] == expected_attachment_id

            return SimpleNamespace(
                id=link_id,
                attachment_id=kwargs["attachment_id"],
            )

    class FakeAdapter:
        channel = "worker-media-test"

        async def fetch_media(
            self,
            *,
            media,
            connection,
        ):
            calls["fetch"] += 1

            assert media.provider_media_id == "media-1"
            assert connection.channel == self.channel
            assert connection.external_account_id == "account-1"
            assert connection.config["provider_setting"] == "opaque"

            return FetchedInboundMedia(
                content=b"data",
                filename="provider-photo.jpg",
                content_type="image/jpeg",
                metadata={
                    "remote": "ok",
                },
            )

    class FakeRegistry:
        def get(self, channel):
            assert channel == "worker-media-test"
            return FakeAdapter()

    class FakeCommercialService:
        def __init__(
            self,
            db,
            *,
            workspace_id,
            actor_id=None,
        ):
            assert workspace_id == user_id

        async def store_attachment(
            self,
            **kwargs,
        ):
            calls["store"] += 1

            assert kwargs["commit"] is False
            assert kwargs["conversation_id"] == conversation_id
            assert kwargs["message_id"] == message_id
            assert kwargs["attachment_id"] == expected_attachment_id
            assert kwargs["content"] == b"data"
            assert kwargs["filename"] == "provider-photo.jpg"

            return SimpleNamespace(
                id=kwargs["attachment_id"],
                filename=kwargs["filename"],
                content_type=kwargs["content_type"],
                size_bytes=len(kwargs["content"]),
                sha256="deadbeef",
            )

    monkeypatch.setattr(
        module,
        "OmnichannelRepository",
        FakeRepo,
    )
    monkeypatch.setattr(
        module,
        "CommercialOperationsService",
        FakeCommercialService,
    )
    monkeypatch.setattr(
        module,
        "register_default_omnichannel_providers",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "get_omnichannel_provider_registry",
        lambda: FakeRegistry(),
    )

    expected_attachment_id = uuid5(
        NAMESPACE_URL,
        (
            "customer-service:external-media:"
            f"{user_id}:"
            "worker-media-test:"
            "account-1:"
            "message-1:"
            "media-1"
        ),
    )

    ctx = FakeCtx(user_id)

    result = await module.materialize_omnichannel_inbound_media_job(
        _payload(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
        ),
        ctx,
    )

    assert result["status"] == "materialized"
    assert result["attachment_id"] == str(expected_attachment_id)

    assert len(ctx.db.executions) == 1

    lock_statement, lock_params = ctx.db.executions[0]

    assert "pg_advisory_xact_lock" in lock_statement
    assert lock_params["lock_key"] == (
        "cs_omnichannel_inbound_media:"
        f"{user_id}:"
        "worker-media-test:"
        "account-1:"
        "message-1:"
        "media-1"
    )

    assert calls == {
        "fetch": 1,
        "store": 1,
        "link": 1,
    }


@pytest.mark.asyncio
async def test_existing_external_media_short_circuits_before_fetch(
    monkeypatch,
):
    from app.domains.customer_service.workflows import (
        omnichannel_jobs as module,
    )

    user_id = uuid4()
    conversation_id = uuid4()
    message_id = uuid4()
    attachment_id = uuid4()
    link_id = uuid4()

    class FakeRepo:
        def __init__(self, db):
            pass

        async def get_external_media(self, **kwargs):
            return SimpleNamespace(
                id=link_id,
                attachment_id=attachment_id,
            )

    class MustNotResolveRegistry:
        def get(self, channel):
            raise AssertionError("existing media must not resolve/fetch provider")

    monkeypatch.setattr(
        module,
        "OmnichannelRepository",
        FakeRepo,
    )
    monkeypatch.setattr(
        module,
        "register_default_omnichannel_providers",
        lambda: (_ for _ in ()).throw(
            AssertionError("existing media must short-circuit first")
        ),
    )
    monkeypatch.setattr(
        module,
        "get_omnichannel_provider_registry",
        lambda: MustNotResolveRegistry(),
    )

    result = await module.materialize_omnichannel_inbound_media_job(
        _payload(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
        ),
        FakeCtx(user_id),
    )

    assert result == {
        "status": "already_materialized",
        "attachment_id": str(attachment_id),
        "external_media_link_id": str(link_id),
        "provider_media_id": "media-1",
    }


@pytest.mark.asyncio
async def test_transient_media_fetch_error_remains_retryable(
    monkeypatch,
):
    from app.domains.customer_service.workflows import (
        omnichannel_jobs as module,
    )

    user_id = uuid4()
    conversation_id = uuid4()
    message_id = uuid4()

    class FakeRepo:
        def __init__(self, db):
            pass

        async def get_external_media(self, **kwargs):
            return None

        async def get_external_message(self, **kwargs):
            return SimpleNamespace(
                conversation_id=conversation_id,
                message_id=message_id,
            )

        async def get_connection(self, **kwargs):
            return SimpleNamespace(
                channel="worker-media-test",
                external_account_id="account-1",
                config={},
            )

    class FakeAdapter:
        channel = "worker-media-test"

        async def fetch_media(self, **kwargs):
            raise OmnichannelProviderTransientError(
                "temporary media outage",
                code="temporary_media_outage",
            )

    class FakeRegistry:
        def get(self, channel):
            return FakeAdapter()

    monkeypatch.setattr(
        module,
        "OmnichannelRepository",
        FakeRepo,
    )
    monkeypatch.setattr(
        module,
        "register_default_omnichannel_providers",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "get_omnichannel_provider_registry",
        lambda: FakeRegistry(),
    )

    ctx = FakeCtx(user_id)

    with pytest.raises(OmnichannelProviderTransientError):
        await module.materialize_omnichannel_inbound_media_job(
            _payload(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=message_id,
            ),
            ctx,
        )

    assert ctx.job.max_attempts == 3


@pytest.mark.asyncio
async def test_permanent_media_fetch_error_stops_retry(
    monkeypatch,
):
    from app.domains.customer_service.workflows import (
        omnichannel_jobs as module,
    )

    user_id = uuid4()
    conversation_id = uuid4()
    message_id = uuid4()

    class FakeRepo:
        def __init__(self, db):
            pass

        async def get_external_media(self, **kwargs):
            return None

        async def get_external_message(self, **kwargs):
            return SimpleNamespace(
                conversation_id=conversation_id,
                message_id=message_id,
            )

        async def get_connection(self, **kwargs):
            return SimpleNamespace(
                channel="worker-media-test",
                external_account_id="account-1",
                config={},
            )

    class FakeAdapter:
        channel = "worker-media-test"

        async def fetch_media(self, **kwargs):
            raise OmnichannelProviderPermanentError(
                "provider rejected media",
                code="media_rejected",
            )

    class FakeRegistry:
        def get(self, channel):
            return FakeAdapter()

    monkeypatch.setattr(
        module,
        "OmnichannelRepository",
        FakeRepo,
    )
    monkeypatch.setattr(
        module,
        "register_default_omnichannel_providers",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "get_omnichannel_provider_registry",
        lambda: FakeRegistry(),
    )

    ctx = FakeCtx(user_id)

    with pytest.raises(OmnichannelProviderPermanentError):
        await module.materialize_omnichannel_inbound_media_job(
            _payload(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=message_id,
            ),
            ctx,
        )

    assert ctx.retryable is False
    assert ctx.job.max_attempts == 3


def test_inbound_media_worker_is_in_default_registry():
    from app.platform.composition import (
        build_default_job_registry,
    )

    registry = build_default_job_registry()

    handler = registry.get(OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB)

    assert handler is not None
    assert handler.__name__ == "materialize_omnichannel_inbound_media_job"
