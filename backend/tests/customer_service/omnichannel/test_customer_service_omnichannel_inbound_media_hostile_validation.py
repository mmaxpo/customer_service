from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.session import SessionLocal
from app.domains.customer_service.integrations.omnichannel.protocol import (
    FetchedInboundMedia,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
    CustomerServiceAttachment,
    CustomerServiceExternalMediaLink,
    MessageSenderType,
)
from app.domains.customer_service.repositories.omnichannel import (
    OmnichannelRepository,
)
from app.domains.customer_service.workflows.omnichannel_job_types import (
    OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
)
from app.identity import create_user
from app.models.schemas import UserCreate
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.tenancy.schemas import WorkspaceCreate
from app.tenancy.service import WorkspaceService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "label",
        "filename",
        "content",
        "declared_size",
        "expected_error",
    ),
    [
        (
            "empty",
            "empty.jpg",
            b"",
            0,
            "Attachment size is not allowed",
        ),
        (
            "oversized",
            "oversized.jpg",
            b"x" * (settings.MAX_ATTACHMENT_BYTES + 1),
            settings.MAX_ATTACHMENT_BYTES + 1,
            "Attachment size is not allowed",
        ),
        (
            "blocked-extension",
            "payload.exe",
            b"benign-content",
            len(b"benign-content"),
            "Executable attachments are not allowed",
        ),
        (
            "mz-disguised",
            "photo.jpg",
            b"MZ" + b"x" * 16,
            18,
            "Executable content is not allowed",
        ),
        (
            "elf-disguised",
            "photo.jpg",
            b"\x7fELF" + b"x" * 16,
            20,
            "Executable content is not allowed",
        ),
        (
            "eicar",
            "photo.jpg",
            b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",
            len(b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"),
            "Malware signature detected",
        ),
        (
            "declared-small-actual-oversized",
            "lying-size.jpg",
            b"x" * (settings.MAX_ATTACHMENT_BYTES + 1),
            4,
            "Attachment size is not allowed",
        ),
    ],
)
async def test_hostile_fetched_media_dead_letters_without_durable_or_physical_artifact(
    tmp_path,
    monkeypatch,
    label,
    filename,
    content,
    declared_size,
    expected_error,
):
    from app.domains.customer_service.workflows import (
        omnichannel_jobs as jobs_module,
    )

    monkeypatch.setattr(
        settings,
        "ATTACHMENT_STORAGE_ROOT",
        str(tmp_path),
    )
    monkeypatch.setattr(
        settings,
        "ATTACHMENT_STORAGE_BACKEND",
        "local",
    )
    monkeypatch.setattr(
        settings,
        "ATTACHMENT_SCAN_MODE",
        "builtin",
    )

    channel = f"media-hostile-{uuid4().hex}"

    external_account_id = "account-1"
    external_thread_id = "thread-1"
    external_message_id = "message-1"
    provider_media_id = "media-1"

    fetch_calls = 0

    class HostileMediaProvider:
        def __init__(self):
            self.channel = channel

        async def fetch_media(
            self,
            *,
            media,
            connection,
        ):
            nonlocal fetch_calls

            fetch_calls += 1

            assert media.provider_media_id == provider_media_id
            assert media.size_bytes == declared_size

            assert connection.channel == channel
            assert connection.external_account_id == external_account_id

            return FetchedInboundMedia(
                content=content,
                filename=filename,
                content_type="image/jpeg",
                metadata={
                    "attack_case": label,
                },
            )

    registry = get_omnichannel_provider_registry()

    test_adapters = dict(registry._adapters)
    test_adapters[channel] = HostileMediaProvider()

    monkeypatch.setattr(
        registry,
        "_adapters",
        test_adapters,
    )

    monkeypatch.setattr(
        jobs_module,
        "register_default_omnichannel_providers",
        lambda: None,
    )

    async with SessionLocal() as db:
        owner = await create_user(
            UserCreate(
                email=f"media-hostile-{label}-{uuid4()}@example.com",
                password=f"Media-Hostile-{uuid4()}",
            ),
            db,
        )

        workspace, _ = await WorkspaceService(db).create_workspace(
            user_id=owner.id,
            payload=WorkspaceCreate(
                name=f"Media Hostile {label} {uuid4()}",
            ),
        )

        user_id = workspace.id

        customer = Customer(
            user_id=user_id,
            workspace_id=user_id,
            name=f"Hostile Media {label}",
        )
        db.add(customer)
        await db.flush()

        conversation = Conversation(
            user_id=user_id,
            workspace_id=user_id,
            customer_id=customer.id,
            channel=channel,
            subject=f"Hostile media {label}",
            status="open",
        )
        db.add(conversation)
        await db.flush()

        message = ConversationMessage(
            conversation_id=conversation.id,
            sender_type=MessageSenderType.CUSTOMER,
            body="",
        )
        db.add(message)
        await db.flush()

        conversation_id = conversation.id
        message_id = message.id

        repo = OmnichannelRepository(db)

        await repo.create_connection(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            config={},
        )

        await repo.link_external_message(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            channel=channel,
            external_account_id=external_account_id,
            external_thread_id=external_thread_id,
            external_message_id=external_message_id,
            direction="inbound",
        )

        payload = {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id),
            "message_id": str(message_id),
            "channel": channel,
            "external_account_id": external_account_id,
            "external_message_id": external_message_id,
            "provider_media_id": provider_media_id,
            "media": {
                "provider_media_id": provider_media_id,
                "filename": filename,
                "content_type": "image/jpeg",
                "size_bytes": declared_size,
                "metadata": {
                    "attack_case": label,
                },
            },
        }

        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
            payload=payload,
            max_attempts=3,
            idempotency_key=(f"hostile-media:{channel}:{provider_media_id}"),
        )

        job_id = job.id

        processed = await JobWorker(
            db,
            worker_id=f"hostile-media-worker-{label}",
        ).run_once(
            job_id=job_id,
        )

        assert processed is not None

        assert processed.status == "dead_letter"
        assert processed.attempts == 1
        assert processed.max_attempts == 1

        assert expected_error in processed.error_message

    assert fetch_calls == 1

    attachment_id = uuid5(
        NAMESPACE_URL,
        (
            "customer-service:external-media:"
            f"{user_id}:"
            f"{channel}:"
            f"{external_account_id}:"
            f"{external_message_id}:"
            f"{provider_media_id}"
        ),
    )

    async with SessionLocal() as verify_db:
        attachment_count = await verify_db.scalar(
            select(func.count(CustomerServiceAttachment.id)).where(
                CustomerServiceAttachment.id == attachment_id
            )
        )

        media_link_count = await verify_db.scalar(
            select(func.count(CustomerServiceExternalMediaLink.id)).where(
                CustomerServiceExternalMediaLink.user_id == user_id,
                CustomerServiceExternalMediaLink.channel == channel,
                CustomerServiceExternalMediaLink.external_account_id
                == external_account_id,
                CustomerServiceExternalMediaLink.external_message_id
                == external_message_id,
                CustomerServiceExternalMediaLink.provider_media_id == provider_media_id,
            )
        )

        assert attachment_count == 0
        assert media_link_count == 0

    expected_storage_path = Path(tmp_path) / str(user_id) / f"{attachment_id.hex}.bin"

    assert not expected_storage_path.exists()

    physical_files = [path for path in Path(tmp_path).rglob("*") if path.is_file()]

    assert physical_files == []
