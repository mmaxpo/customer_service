from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import HTTPException
from sqlalchemy import text

from fastapi.encoders import jsonable_encoder

from app.domains.customer_service.integrations.omnichannel.errors import (
    OmnichannelProviderError,
)
from app.domains.customer_service.integrations.omnichannel.retry_policy import (
    OmnichannelRetryPolicy,
)
from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)
from app.domains.customer_service.integrations.omnichannel.protocol import (
    NormalizedInboundMedia,
    OmnichannelProviderConnectionContext,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.domains.customer_service.schemas.omnichannel import (
    OmnichannelOutboundAttachment,
    OmnichannelOutboundMessage,
)
from app.domains.customer_service.repositories.omnichannel import (
    OmnichannelRepository,
)
from app.domains.customer_service.services.commercial_operations import (
    CommercialOperationsService,
)
from app.domains.customer_service.services.omnichannel import (
    CustomerServiceOmnichannelService,
)
from app.domains.customer_service.workflows.omnichannel_job_types import (
    OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
    OMNICHANNEL_OUTBOUND_SEND_JOB,
)

__all__ = (
    "OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB",
    "OMNICHANNEL_OUTBOUND_SEND_JOB",
    "materialize_omnichannel_inbound_media_job",
    "register_customer_service_omnichannel_job_handlers",
    "send_omnichannel_outbound_job",
)


def _inbound_media_attachment_id(
    *,
    user_id: UUID,
    channel: str,
    external_account_id: str,
    external_message_id: str,
    provider_media_id: str,
) -> UUID:
    identity = (
        "customer-service:external-media:"
        f"{user_id}:"
        f"{channel}:"
        f"{external_account_id}:"
        f"{external_message_id}:"
        f"{provider_media_id}"
    )
    return uuid5(NAMESPACE_URL, identity)


async def materialize_omnichannel_inbound_media_job(
    payload: dict,
    ctx,
) -> dict:
    user_id = UUID(str(ctx.job.user_id or payload.get("user_id")))
    conversation_id = UUID(str(payload["conversation_id"]))
    message_id = UUID(str(payload["message_id"]))

    channel = str(payload["channel"])
    external_account_id = str(payload["external_account_id"])
    external_message_id = str(payload["external_message_id"])
    provider_media_id = str(payload["provider_media_id"])

    media = NormalizedInboundMedia.model_validate(payload["media"])

    if media.provider_media_id != provider_media_id:
        exc = OmnichannelProviderError(
            "Inbound media job provider-media identity mismatch",
            code="media_identity_mismatch",
        )
        ctx.retryable = False
        raise exc

    repo = OmnichannelRepository(ctx.db)

    # Serialize all materialization attempts for one logical
    # provider media object. This closes the check-then-insert
    # race across duplicate/replayed jobs running in separate
    # database sessions.
    lock_key = (
        "cs_omnichannel_inbound_media:"
        f"{user_id}:"
        f"{channel}:"
        f"{external_account_id}:"
        f"{external_message_id}:"
        f"{provider_media_id}"
    )

    await ctx.db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
        {
            "lock_key": lock_key,
        },
    )

    existing = await repo.get_external_media(
        user_id=user_id,
        channel=channel,
        external_account_id=external_account_id,
        external_message_id=external_message_id,
        provider_media_id=provider_media_id,
    )

    if existing is not None:
        return {
            "status": "already_materialized",
            "attachment_id": str(existing.attachment_id),
            "external_media_link_id": str(existing.id),
            "provider_media_id": provider_media_id,
        }

    external_message = await repo.get_external_message(
        user_id=user_id,
        channel=channel,
        external_account_id=external_account_id,
        external_message_id=external_message_id,
    )

    if (
        external_message is None
        or external_message.conversation_id != conversation_id
        or external_message.message_id != message_id
    ):
        exc = OmnichannelProviderError(
            "Inbound media job does not match durable external message",
            code="external_message_mismatch",
        )
        ctx.retryable = False
        raise exc

    connection = await repo.get_connection(
        user_id=user_id,
        channel=channel,
        external_account_id=external_account_id,
    )

    if connection is None:
        exc = OmnichannelProviderError(
            "Inbound media channel connection not found",
            code="channel_connection_missing",
        )
        ctx.retryable = False
        raise exc

    register_default_omnichannel_providers()

    adapter = get_omnichannel_provider_registry().get(channel)

    connection_context = OmnichannelProviderConnectionContext(
        channel=connection.channel,
        external_account_id=(connection.external_account_id),
        config=dict(connection.config or {}),
    )

    try:
        fetched = await adapter.fetch_media(
            media=media,
            connection=connection_context,
        )
    except NotImplementedError as exc:
        ctx.retryable = False
        raise OmnichannelProviderError(
            str(exc),
            code="media_fetch_not_implemented",
        ) from exc
    except OmnichannelProviderError as exc:
        decision = OmnichannelRetryPolicy(
            max_attempts=ctx.job.max_attempts,
        ).decide(
            exc=exc,
            attempt=ctx.job.attempts,
        )

        if not decision.should_retry:
            ctx.retryable = False

        raise

    attachment_id = _inbound_media_attachment_id(
        user_id=user_id,
        channel=channel,
        external_account_id=external_account_id,
        external_message_id=external_message_id,
        provider_media_id=provider_media_id,
    )

    filename = fetched.filename or media.filename or f"{provider_media_id}.bin"
    content_type = (
        fetched.content_type or media.content_type or "application/octet-stream"
    )

    try:
        attachment = await CommercialOperationsService(
            ctx.db,
            workspace_id=user_id,
        ).store_attachment(
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
            filename=filename,
            content_type=content_type,
            content=fetched.content,
            commit=False,
        )
    except HTTPException:
        # Product validation failures such as malware,
        # invalid ownership, or disallowed size are not
        # expected to improve on provider retry.
        ctx.retryable = False
        raise

    link = await repo.link_external_media(
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        attachment_id=attachment.id,
        channel=channel,
        external_account_id=external_account_id,
        external_message_id=external_message_id,
        provider_media_id=provider_media_id,
        meta={
            "filename": attachment.filename,
            "content_type": attachment.content_type,
            "size_bytes": attachment.size_bytes,
            "sha256": attachment.sha256,
            "provider_metadata": dict(fetched.metadata or {}),
        },
    )

    return {
        "status": "materialized",
        "attachment_id": str(attachment.id),
        "external_media_link_id": str(link.id),
        "provider_media_id": provider_media_id,
        "sha256": attachment.sha256,
        "size_bytes": attachment.size_bytes,
    }


async def send_omnichannel_outbound_job(
    payload: dict,
    ctx,
) -> dict:
    user_id = ctx.job.user_id or payload.get("user_id")
    if user_id is None:
        raise ValueError("omnichannel outbound job requires user_id")

    register_default_omnichannel_providers()

    try:
        result = await CustomerServiceOmnichannelService(ctx.db).send_outbound_message(
            user_id=UUID(str(user_id)),
            payload=OmnichannelOutboundMessage(
                conversation_id=UUID(str(payload["conversation_id"])),
                body=payload["body"],
                sender_type=payload.get("sender_type") or "agent",
                external_thread_id=payload.get("external_thread_id"),
                idempotency_key=payload.get("idempotency_key"),
                attachments=[
                    OmnichannelOutboundAttachment(
                        attachment_id=UUID(str(attachment_id))
                    )
                    for attachment_id in (payload.get("attachment_ids") or [])
                ],
                meta=payload.get("meta"),
            ),
        )
    except OmnichannelProviderError as exc:
        decision = OmnichannelRetryPolicy(
            max_attempts=ctx.job.max_attempts,
        ).decide(
            exc=exc,
            attempt=ctx.job.attempts,
        )

        if not decision.should_retry:
            ctx.retryable = False

        raise

    return jsonable_encoder(result)


def register_customer_service_omnichannel_job_handlers(registry) -> None:
    registry.register(
        OMNICHANNEL_OUTBOUND_SEND_JOB,
        send_omnichannel_outbound_job,
    )
    registry.register(
        OMNICHANNEL_INBOUND_MEDIA_MATERIALIZE_JOB,
        materialize_omnichannel_inbound_media_job,
    )
