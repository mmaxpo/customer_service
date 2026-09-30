"""
Public Runtime workflow-execution boundary.

Application bridges may execute durable workflows through this module
without importing Runtime engine implementation modules directly.
"""

from app.runtime.engine.executor import (
    execute_workflow_dag,
)

__all__ = [
    "execute_workflow_dag",
]
