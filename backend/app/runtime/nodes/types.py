from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable


class NodeRunResult(Dict[str, Any]):
    pass


@runtime_checkable
class RuntimeContext(Protocol):
    user_id: Any
    thread_id: Any
    request: Any
    db: Any
    app: Any
    extras: Dict[str, Any]
    tools: Any
    services: Any
