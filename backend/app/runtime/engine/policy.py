def get_node_type(node_def: dict) -> str | None:
    """
    Return the node type from a React Flow node definition.

    Node type is stored in:

        node_def["data"]["nodeType"]

    Args:
        node_def: Workflow node definition.

    Returns:
        str | None: Node type such as "kb.search", "response", or None.

    Example:
        node_type = get_node_type({
            "id": "n1",
            "data": {"nodeType": "response"},
        })

        assert node_type == "response"
    """
    return (node_def.get("data") or {}).get("nodeType")


class ExecutionPolicy:
    """
    Runtime execution limits and scheduling rules.

    The engine decides which nodes are runnable.
    The policy decides how many runnable nodes should execute now.

    Current responsibilities:
        - enforce max_steps
        - enforce max_concurrency
        - run only one control.loop node at a time

    Future responsibilities:
        - per-plan limits
        - cost limits
        - priority rules
        - tenant-level concurrency
        - default timeout/retry policy

    Example:
        policy = ExecutionPolicy(
            max_steps=500,
            max_concurrency=8,
        )

        while policy.can_continue(steps=steps):
            batch = policy.select_batch(
                ready=ready,
                nodes_by_id=nodes_by_id,
            )
    """

    def __init__(
        self,
        *,
        max_steps: int = 500,
        max_concurrency: int = 8,
    ) -> None:
        """

        Create execution policy with safe minimum values.

        Args:

            max_steps: Maximum scheduler loop iterations.

            max_concurrency: Maximum nodes to execute in one batch.

        Example:

            policy = ExecutionPolicy(max_steps=100, max_concurrency=4)

            assert policy.max_steps == 100

            assert policy.max_concurrency == 4

        """
        self.max_steps = max(1, int(max_steps or 1))
        self.max_concurrency = max(1, int(max_concurrency or 1))

    def select_batch(
        self,
        *,
        ready: list[str],
        nodes_by_id: dict,
    ) -> list[str]:
        """

        Select which ready nodes should execute in the current step.

        Special rule:

            If any ready node is "control.loop", execute only one loop node.

            This prevents loop control from racing with other nodes.

        Otherwise:

            Execute up to max_concurrency ready nodes.

        Example:

            ready = ["kb", "sentiment", "reply"]

            batch = policy.select_batch(

                ready=ready,

                nodes_by_id=nodes_by_id,

            )

            assert len(batch) <= policy.max_concurrency

        """
        loop_ready = [
            node_id
            for node_id in ready
            if get_node_type(nodes_by_id[node_id]) == "control.loop"
        ]

        if loop_ready:
            return [sorted(loop_ready)[0]]

        return ready[: self.max_concurrency]

    def can_continue(self, *, steps: int) -> bool:
        """
        Return whether the scheduler loop may continue.
        Args:
            steps: Number of loop iterations already executed.
        Returns:

            bool: True if steps is still below max_steps.

        Example:

            policy = ExecutionPolicy(max_steps=3)

            assert policy.can_continue(steps=0) is True

            assert policy.can_continue(steps=3) is False

        """
        return steps < self.max_steps


def batch_contains_response_node(
    *,
    batch: list[str],
    nodes_by_id: dict,
) -> bool:
    """
    Return True if the executed batch contains a response node.

    In this runtime, a response node means the workflow has produced its final
    answer and the scheduler loop should stop.

    Example:
        if batch_contains_response_node(batch=batch, nodes_by_id=nodes_by_id):
            break
    """
    return any(get_node_type(nodes_by_id[node_id]) == "response" for node_id in batch)
