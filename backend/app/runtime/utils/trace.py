from __future__ import annotations
from typing import Any, Dict, List


def format_run_trace(
    events: List[Dict[str, Any]] | None, *, max_lines: int = 300
) -> str:
    """
    Compact timeline output for debugging.
    Includes: node_start/node_end/node_skip/node_error/run_paused/run_resume/run_start/run_end/run_cancelled
    """
    events = events or []
    lines: List[str] = []

    keep = {
        "run_start",
        "run_resume",
        "run_end",
        "run_paused",
        "run_cancelled",
        "node_start",
        "node_end",
        "node_skip",
        "node_error",
        "loop_continue",
    }

    for ev in events:
        et = ev.get("event")
        if et not in keep:
            continue

        ra = ev.get("run_attempt")
        prefix = f"[attempt={ra}] " if ra is not None else ""

        if et.startswith("run_"):
            if et == "run_paused":
                intr = ev.get("interrupt") or {}
                lines.append(f"{prefix}{et} interrupt={intr}")
            else:
                lines.append(f"{prefix}{et}")
        elif et in {"node_start", "node_end"}:
            nid = ev.get("node_id")
            nt = ev.get("node_type")
            lines.append(f"{prefix}{et} {nid} ({nt})")
        elif et == "node_skip":
            nid = ev.get("node_id")
            reason = ev.get("reason")
            lines.append(f"{prefix}{et} {nid} reason={reason}")
        elif et == "node_error":
            nid = ev.get("node_id")
            err = ev.get("error")
            lines.append(f"{prefix}{et} {nid} error={err}")
        elif et == "loop_continue":
            nid = ev.get("node_id")
            reset = ev.get("reset")
            lines.append(f"{prefix}{et} {nid} reset={reset}")

        if len(lines) >= max_lines:
            lines.append("... (trace truncated)")
            break

    return "\n".join(lines)
