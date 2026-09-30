from __future__ import annotations

import logging
import pytest

from tests.database_isolation import (
    bootstrap_isolated_test_database,
    cleanup_isolated_test_database,
)


# This must run before importing application modules. app.core.session creates
# its engine at import time and must bind to the isolated database.
bootstrap_isolated_test_database()

from app.node_registration import register_application_nodes  # noqa: E402

_log = logging.getLogger("tests")


class DummyAppState:
    # add anything later if some nodes require it
    pass


class DummyApp:
    def __init__(self) -> None:
        self.state = DummyAppState()


class DummyCtx:
    """
    Minimal RuntimeContext for unit tests.
    Nodes we test (trigger/router/set/join/response) don't need db/request.
    """

    def __init__(self) -> None:
        self.user_id = "test-user"
        self.thread_id = "test-thread"
        self.request = None
        self.db = None
        self.app = DummyApp()
        self.logger = _log
        self.config = None


@pytest.fixture(scope="session", autouse=True)
def _register_nodes_once():
    # Ensure registry has all built-in node types
    register_application_nodes()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_database():
    yield
    cleanup_isolated_test_database()


@pytest.fixture()
def ctx() -> DummyCtx:
    return DummyCtx()


class InMemoryRunStore:
    def __init__(self):
        self._runs = {}  # UUID -> dict

    async def create_run(
        self, *, run_id, user_id=None, thread_id=None, workflow=None, state=None
    ):
        self._runs.setdefault(
            run_id, {"status": "running", "workflow": workflow, "state": state}
        )

    async def load_run(self, *, run_id):
        return self._runs.get(run_id)

    async def update_run(self, *, run_id, status, state, extra=None):
        row = self._runs.setdefault(
            run_id, {"workflow": None, "state": None, "status": None}
        )
        row["status"] = status
        row["state"] = state
        if extra is not None:
            row["extra"] = extra
