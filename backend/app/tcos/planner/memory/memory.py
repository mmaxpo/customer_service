from __future__ import annotations

import time

from app.tcos.planner.memory.models import MemoryCandidate, PlanningMemoryEntry
from app.tcos.planner.runtime.intent import PlannerIntent
from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.planner.runtime.planning_context import PlanningContext


class PlanningMemory:
    _entries: dict[str, PlanningMemoryEntry] = {}

    def retrieve(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None = None,
    ) -> list[MemoryCandidate]:
        return [
            MemoryCandidate(
                candidate=entry.candidate,
                similarity=entry.confidence,
                metadata={
                    "memory_entry_id": entry.id,
                    "success_count": entry.success_count,
                    "failure_count": entry.failure_count,
                    "success_rate": entry.success_rate,
                },
            )
            for entry in self._entries.values()
            if entry.intent_name == intent.name
        ]

    def record_success(
        self,
        *,
        intent_name: str,
        candidate: PlanCandidate,
        latency_ms: float | None = None,
        cost: float | None = None,
    ) -> PlanningMemoryEntry:
        entry = self._entry_for(intent_name=intent_name, candidate=candidate)
        entry.success_count += 1
        entry.last_used_at_ts = time.time()
        entry.updated_at_ts = entry.last_used_at_ts

        if latency_ms is not None:
            entry.average_latency_ms = self._rolling_average(
                previous=entry.average_latency_ms,
                count=entry.success_count,
                new_value=latency_ms,
            )

        if cost is not None:
            entry.average_cost = self._rolling_average(
                previous=entry.average_cost,
                count=entry.success_count,
                new_value=cost,
            )

        self._entries[entry.id] = entry
        return entry

    def record_failure(
        self,
        *,
        intent_name: str,
        candidate: PlanCandidate,
    ) -> PlanningMemoryEntry:
        entry = self._entry_for(intent_name=intent_name, candidate=candidate)
        entry.failure_count += 1
        entry.updated_at_ts = time.time()
        self._entries[entry.id] = entry
        return entry

    def clear(self) -> None:
        self._entries.clear()

    def _entry_for(
        self,
        *,
        intent_name: str,
        candidate: PlanCandidate,
    ) -> PlanningMemoryEntry:
        entry_id = f"{intent_name}:{candidate.id}"

        existing = self._entries.get(entry_id)
        if existing is not None:
            return existing.model_copy(deep=True)

        return PlanningMemoryEntry(
            id=entry_id,
            intent_name=intent_name,
            candidate=candidate.model_copy(deep=True),
        )

    def _rolling_average(
        self,
        *,
        previous: float | None,
        count: int,
        new_value: float,
    ) -> float:
        if previous is None or count <= 1:
            return new_value

        return ((previous * (count - 1)) + new_value) / count
