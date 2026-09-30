from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.models.models import PlatformEvent


@dataclass
class EventContext:
    db: Any
    event: PlatformEvent


EventHandler = Callable[
    [PlatformEvent, EventContext],
    Awaitable[dict[str, Any] | None],
]


class EventHandlerRegistry:
    def __init__(self):
        self._handlers: dict[
            str,
            list[EventHandler],
        ] = {}

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        if not event_type or not event_type.strip():
            raise ValueError("event_type is required")

        handlers = self._handlers.setdefault(
            event_type,
            [],
        )

        # Composition may safely be executed more than once.
        if handler not in handlers:
            handlers.append(handler)

    def handlers_for(
        self,
        event_type: str,
    ) -> list[EventHandler]:
        handlers = list(
            self._handlers.get(
                event_type,
                [],
            )
        )

        handlers.extend(
            self._handlers.get(
                "*",
                [],
            )
        )

        return handlers

    def event_types(
        self,
    ) -> set[str]:
        return set(self._handlers.keys())


default_event_registry = EventHandlerRegistry()

# Compatibility/default application composition.
#
# The registry above contains no knowledge of products, Runtime,
# capabilities, or concrete handler modules. Application wiring is
# centralized in app.platform.composition.
