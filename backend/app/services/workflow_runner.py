"""
Deprecated.

Do not use this module for workflow execution.

The only supported workflow execution path is:

    app.runtime.engine.executor

This file intentionally stays as a guard so old imports fail loudly instead of
silently creating a second workflow runtime.
"""


def run_workflow(*args, **kwargs):
    raise RuntimeError(
        "app.services.workflow_runner is deprecated. "
        "Use app.runtime.engine.executor instead."
    )
