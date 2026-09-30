from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IdentityServices:
    """Who this runtime execution belongs to."""

    user_id: Any = None
    tenant_id: Any = None
    thread_id: Any = None


@dataclass
class DataServices:
    """Data resources available to runtime execution."""

    db: Any = None
    cache: Any = None
    vector_store: Any = None
    storage: Any = None


@dataclass
class AIServices:
    """AI resources available to runtime execution."""

    tools: Any = None
    llm: Any = None
    agent_llm: Any = None
    embeddings: Any = None
    reranker: Any = None


@dataclass
class BusinessServices:
    """
    Business and provider resources injected into Runtime execution.

    Runtime Core owns the container shape only.
    Product and Provider implementations are installed externally.
    """

    shopify: Any = None
    customer_service: Any = None
    knowledge: Any = None


@dataclass
class RuntimeKernelServices:
    """Durable workflow resources used by the runtime engine."""

    run_store: Any = None
    timeline: Any = None
    snapshots: Any = None
    artifacts: Any = None
    memory: Any = None


@dataclass
class InfrastructureServices:
    """Infrastructure resources used while workflows execute."""

    event_sink: Any = None
    jobs: Any = None
    scheduler: Any = None
    event_bus: Any = None


@dataclass
class RuntimeServices:
    """
    Resources available to one runtime execution.

    The grouped attributes are intentionally preserved during R1 so this
    structural refactor does not change runtime behavior.
    """

    identity: IdentityServices
    data: DataServices
    ai: AIServices
    business: BusinessServices
    runtime: RuntimeKernelServices
    infrastructure: InfrastructureServices

    capabilities: Any = None
    capability_system: Any = None
    capability_registry: Any = None
    capability_executors: Any = None
    capability_outcome_reporter: Any = None
    task_verifiers: Any = None
    task_verification: Any = None

    @property
    def db(self) -> Any:
        """Backward-compatible shortcut for data.db."""

        return self.data.db

    @db.setter
    def db(self, value: Any) -> None:
        self.data.db = value

    @property
    def tools(self) -> Any:
        """Backward-compatible shortcut for ai.tools."""

        return self.ai.tools

    @tools.setter
    def tools(self, value: Any) -> None:
        self.ai.tools = value
