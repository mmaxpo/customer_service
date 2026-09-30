from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PlatformEvent
from app.runtime.capabilities.execution.installation.repository import (
    normalize_installation_user_id,
)


PROVIDER_INSTALLATION_EVENT_SOURCE = (
    "runtime.provider_installations"
)

PROVIDER_INSTALLATION_EVENT_PREFIX = (
    "runtime.provider.installation."
)

PROVIDER_INSTALLATION_EVENT_TYPES = frozenset(
    {
        "runtime.provider.installation.connected",
        "runtime.provider.installation.enabled",
        "runtime.provider.installation.disabled",
        "runtime.provider.installation.verified",
        (
            "runtime.provider.installation."
            "verification_failed"
        ),
        "runtime.provider.installation.reconciled",
    }
)

PROVIDER_INSTALLATION_OUTCOME_TYPES = {
    "connected": (
        "runtime.provider.installation.connected"
    ),
    "enabled": (
        "runtime.provider.installation.enabled"
    ),
    "disabled": (
        "runtime.provider.installation.disabled"
    ),
    "verified": (
        "runtime.provider.installation.verified"
    ),
    "failed": (
        "runtime.provider.installation."
        "verification_failed"
    ),
    "reconciled": (
        "runtime.provider.installation.reconciled"
    ),
}


class ProviderInstallationHistoryQuery:
    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def list_events(
        self,
        *,
        user_id: Any,
        provider_id: str,
        tenant_id: str | None = None,
        event_type: str | None = None,
        outcome: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PlatformEvent]:
        normalized_user_id = (
            normalize_installation_user_id(
                user_id
            )
        )
        normalized_provider_id = (
            provider_id.strip().lower()
        )

        if not normalized_provider_id:
            raise ValueError(
                "provider_id must not be empty"
            )

        normalized_event_type = (
            event_type.strip()
            if event_type is not None
            else None
        )

        if (
            normalized_event_type is not None
            and normalized_event_type
            not in PROVIDER_INSTALLATION_EVENT_TYPES
        ):
            raise ValueError(
                "unsupported provider installation "
                "event_type"
            )

        normalized_outcome = (
            outcome.strip().lower()
            if outcome is not None
            else None
        )

        if (
            normalized_outcome is not None
            and normalized_outcome
            not in PROVIDER_INSTALLATION_OUTCOME_TYPES
        ):
            raise ValueError(
                "unsupported provider installation "
                "outcome"
            )

        if (
            normalized_event_type is not None
            and normalized_outcome is not None
            and normalized_event_type
            != PROVIDER_INSTALLATION_OUTCOME_TYPES[
                normalized_outcome
            ]
        ):
            return []

        provider_expression = cast(
            PlatformEvent.payload[
                "provider_id"
            ].astext,
            String,
        )

        stmt = (
            select(PlatformEvent)
            .where(
                PlatformEvent.user_id
                == normalized_user_id,
                PlatformEvent.source
                == PROVIDER_INSTALLATION_EVENT_SOURCE,
                provider_expression
                == normalized_provider_id,
            )
            .order_by(
                PlatformEvent.created_at.desc(),
                PlatformEvent.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        selected_type = normalized_event_type

        if (
            selected_type is None
            and normalized_outcome is not None
        ):
            selected_type = (
                PROVIDER_INSTALLATION_OUTCOME_TYPES[
                    normalized_outcome
                ]
            )

        if selected_type is not None:
            stmt = stmt.where(
                PlatformEvent.event_type
                == selected_type
            )
        else:
            stmt = stmt.where(
                PlatformEvent.event_type.in_(
                    PROVIDER_INSTALLATION_EVENT_TYPES
                )
            )

        if tenant_id is not None:
            normalized_tenant_id = (
                tenant_id.strip()
            )

            stmt = stmt.where(
                cast(
                    PlatformEvent.payload[
                        "tenant_id"
                    ].astext,
                    String,
                )
                == normalized_tenant_id
            )

        if created_from is not None:
            stmt = stmt.where(
                PlatformEvent.created_at
                >= created_from
            )

        if created_to is not None:
            stmt = stmt.where(
                PlatformEvent.created_at
                <= created_to
            )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())


def sanitize_provider_installation_event(
    event: PlatformEvent,
) -> dict[str, Any]:
    payload = dict(event.payload or {})

    shop_payload = payload.get("shop")
    shop = (
        {
            "id": shop_payload.get("id"),
            "name": shop_payload.get("name"),
            "myshopify_domain": (
                shop_payload.get(
                    "myshopify_domain"
                )
            ),
        }
        if isinstance(shop_payload, dict)
        else None
    )

    return {
        "id": event.id,
        "event_type": event.event_type,
        "source": event.source,
        "status": event.status,
        "provider_id": payload.get(
            "provider_id"
        ),
        "installation_id": _optional_uuid(
            payload.get("installation_id")
        ),
        "installation_ids": [
            item
            for item in (
                _optional_uuid(value)
                for value in (
                    payload.get(
                        "installation_ids"
                    )
                    or []
                )
            )
            if item is not None
        ],
        "tenant_id": payload.get(
            "tenant_id"
        ),
        "integration_kind": payload.get(
            "integration_kind"
        ),
        "integration_connection_id": (
            payload.get(
                "integration_connection_id"
            )
        ),
        "enabled": payload.get("enabled"),
        "configuration_state": payload.get(
            "configuration_state"
        ),
        "authentication_state": payload.get(
            "authentication_state"
        ),
        "verification_state": payload.get(
            "verification_state"
        ),
        "failure_code": payload.get(
            "failure_code"
        ),
        "installation_version": payload.get(
            "version"
        ),
        "discovered": payload.get(
            "discovered"
        ),
        "projected": payload.get(
            "projected"
        ),
        "shop": shop,
        "created_at": event.created_at,
    }


def _optional_uuid(
    value: Any,
) -> UUID | None:
    if value in (None, ""):
        return None

    try:
        return UUID(str(value))
    except (
        TypeError,
        ValueError,
        AttributeError,
    ):
        return None


__all__ = [
    "PROVIDER_INSTALLATION_EVENT_PREFIX",
    "PROVIDER_INSTALLATION_EVENT_SOURCE",
    "PROVIDER_INSTALLATION_EVENT_TYPES",
    "PROVIDER_INSTALLATION_OUTCOME_TYPES",
    "ProviderInstallationHistoryQuery",
    "sanitize_provider_installation_event",
]
