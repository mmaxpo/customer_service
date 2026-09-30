from __future__ import annotations

import json

from app.platform.realtime.schemas import RealtimeEvent


def encode_sse_event(event: RealtimeEvent) -> str:
    data = event.model_dump(mode="json")
    return (
        f"event: {event.type}\\ndata: {json.dumps(data, separators=(',', ':'))}\\n\\n"
    )


def encode_sse_heartbeat() -> str:
    return "event: heartbeat\\ndata: {}\\n\\n"
