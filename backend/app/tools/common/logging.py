from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict

logger = logging.getLogger("app.tools")


def _json(obj: Dict[str, Any]) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)


def tool_log(event: str, **fields: Any) -> None:
    logger.info("%s %s", event, _json(fields))


@contextmanager
def tool_span(name: str, **fields: Any):
    t0 = time.time()
    tool_log("tool.start", name=name, **fields)
    try:
        yield
        tool_log("tool.end", name=name, ms=int((time.time() - t0) * 1000), ok=True)
    except Exception as e:
        tool_log(
            "tool.end",
            name=name,
            ms=int((time.time() - t0) * 1000),
            ok=False,
            error=str(e),
        )
        raise
