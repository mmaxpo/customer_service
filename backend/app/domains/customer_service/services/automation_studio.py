"""Composed facade for the customer-service automation studio.

Each job lives in its own mixin module so routes retain one service entry point
while a person can read workflow, proposal, testing, version, or review code in isolation.
"""

from __future__ import annotations

from .automation_studio_proposals import ProposalsStudioMixin
from .automation_studio_review import ReviewStudioMixin
from .automation_studio_testing import TestingStudioMixin
from .automation_studio_versions import VersionsStudioMixin
from .automation_studio_workflows import WorkflowsStudioMixin
from app.workflow_operations.versions.repository import WorkflowVersionRepository


class AutomationStudioService(
    WorkflowsStudioMixin,
    ProposalsStudioMixin,
    TestingStudioMixin,
    VersionsStudioMixin,
    ReviewStudioMixin,
):
    """Single route-facing service composed from focused job mixins."""

    def __init__(self, db):
        self.db = db
        self.versions = WorkflowVersionRepository(db)
