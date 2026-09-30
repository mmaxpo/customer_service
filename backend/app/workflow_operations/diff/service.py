from __future__ import annotations

from typing import Any


class WorkflowStateDiffService:
    """
    Deterministic workflow state comparison engine.

    Compares:
    - vars
    - results
    - errors
    - finished/skipped sets
    - last output
    - interrupt state

    Foundation for:
    - replay comparison
    - regression detection
    - evaluation engine
    """

    def compare_states(
        self,
        *,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:

        before_meta = before.get("meta") or {}
        after_meta = after.get("meta") or {}

        diff = {
            "changed": False,
            "vars_changed": self._dict_diff(
                before.get("vars") or {},
                after.get("vars") or {},
            ),
            "results_changed": self._dict_diff(
                before.get("results") or {},
                after.get("results") or {},
            ),
            "errors_changed": self._dict_diff(
                before.get("errors") or {},
                after.get("errors") or {},
            ),
            "finished_changed": self._set_diff(
                before_meta.get("finished") or [],
                after_meta.get("finished") or [],
            ),
            "skipped_changed": self._set_diff(
                before_meta.get("skipped") or [],
                after_meta.get("skipped") or [],
            ),
            "last_changed": (before.get("last") != after.get("last")),
            "interrupt_changed": (
                before_meta.get("interrupt") != after_meta.get("interrupt")
            ),
        }

        diff["changed"] = any(
            [
                diff["vars_changed"]["changed"],
                diff["results_changed"]["changed"],
                diff["errors_changed"]["changed"],
                diff["finished_changed"]["changed"],
                diff["skipped_changed"]["changed"],
                diff["last_changed"],
                diff["interrupt_changed"],
            ]
        )

        return diff

    def _dict_diff(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:

        before_keys = set(before.keys())
        after_keys = set(after.keys())

        added = sorted(after_keys - before_keys)
        removed = sorted(before_keys - after_keys)

        changed_values = []

        for key in sorted(before_keys & after_keys):
            if before[key] != after[key]:
                changed_values.append(
                    {
                        "key": key,
                        "before": before[key],
                        "after": after[key],
                    }
                )

        return {
            "changed": bool(added or removed or changed_values),
            "added": added,
            "removed": removed,
            "changed_values": changed_values,
        }

    def _set_diff(
        self,
        before: list[str],
        after: list[str],
    ) -> dict[str, Any]:

        before_set = set(before)
        after_set = set(after)

        added = sorted(after_set - before_set)
        removed = sorted(before_set - after_set)

        return {
            "changed": bool(added or removed),
            "added": added,
            "removed": removed,
        }
