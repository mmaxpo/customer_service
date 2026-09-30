from __future__ import annotations

from collections import defaultdict, deque

from app.tcos.planner.business_ir.models import BusinessPlan


def tasks_by_id(plan: BusinessPlan) -> dict[str, object]:
    return {task.id: task for task in plan.tasks}


def outgoing_edges(plan: BusinessPlan) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)

    for task in plan.tasks:
        out.setdefault(task.id, [])

    for edge in plan.edges:
        out[edge.source].append(edge.target)

    for values in out.values():
        values.sort()

    return dict(out)


def incoming_edges(plan: BusinessPlan) -> dict[str, list[str]]:
    inc: dict[str, list[str]] = defaultdict(list)

    for task in plan.tasks:
        inc.setdefault(task.id, [])

    for edge in plan.edges:
        inc[edge.target].append(edge.source)

    for values in inc.values():
        values.sort()

    return dict(inc)


def entry_task_ids(plan: BusinessPlan) -> list[str]:
    incoming = incoming_edges(plan)
    return sorted([task.id for task in plan.tasks if not incoming.get(task.id)])


def exit_task_ids(plan: BusinessPlan) -> list[str]:
    outgoing = outgoing_edges(plan)
    return sorted([task.id for task in plan.tasks if not outgoing.get(task.id)])


def topological_task_ids(plan: BusinessPlan) -> list[str]:
    outgoing = outgoing_edges(plan)
    incoming = incoming_edges(plan)
    indegree = {task.id: len(incoming.get(task.id, [])) for task in plan.tasks}
    queue = deque(
        sorted([task_id for task_id, count in indegree.items() if count == 0])
    )
    ordered: list[str] = []

    while queue:
        task_id = queue.popleft()
        ordered.append(task_id)

        for target in outgoing.get(task_id, []):
            indegree[target] -= 1

            if indegree[target] == 0:
                queue.append(target)

        queue = deque(sorted(queue))

    if len(ordered) != len(plan.tasks):
        return []

    return ordered


def parallel_groups(plan: BusinessPlan) -> list[list[str]]:
    outgoing = outgoing_edges(plan)
    incoming = incoming_edges(plan)
    indegree = {task.id: len(incoming.get(task.id, [])) for task in plan.tasks}
    ready = sorted([task_id for task_id, count in indegree.items() if count == 0])
    groups: list[list[str]] = []

    while ready:
        current = ready
        groups.append(current)
        next_ready: list[str] = []

        for task_id in current:
            for target in outgoing.get(task_id, []):
                indegree[target] -= 1

                if indegree[target] == 0:
                    next_ready.append(target)

        ready = sorted(next_ready)

    return groups if sum(len(group) for group in groups) == len(plan.tasks) else []


def critical_path_task_ids(plan: BusinessPlan) -> list[str]:
    ordered = topological_task_ids(plan)

    if not ordered:
        return []

    outgoing = outgoing_edges(plan)
    duration_by_id = {task.id: task.estimated_duration_ms or 1 for task in plan.tasks}
    distance: dict[str, int] = {
        task_id: duration_by_id.get(task_id, 1) for task_id in ordered
    }
    previous: dict[str, str | None] = {task_id: None for task_id in ordered}

    for task_id in ordered:
        for target in outgoing.get(task_id, []):
            candidate = distance[task_id] + duration_by_id.get(target, 1)

            if candidate > distance.get(target, 0):
                distance[target] = candidate
                previous[target] = task_id

    end = max(distance, key=lambda task_id: (distance[task_id], task_id))
    path: list[str] = []

    while end is not None:
        path.append(end)
        end = previous[end]

    return list(reversed(path))
