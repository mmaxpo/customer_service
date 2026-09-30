"""
Public workflow-validation boundary for Runtime consumers.

Application and Product code should import validation behavior from
this module rather than depending directly on Runtime engine internals.
"""

from app.runtime.engine.validator import (
    ValidationError,
    validate_workflow,
)

__all__ = [
    "ValidationError",
    "validate_workflow",
]
