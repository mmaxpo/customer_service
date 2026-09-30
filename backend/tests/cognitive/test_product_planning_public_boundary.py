from __future__ import annotations

import ast
from pathlib import Path

from app.tcos.planner.product_planning import (
    PlanCandidate,
    PlannerIntent,
    PlannerIntentName,
    PlanningContext,
    ProductBusinessPlanBuilder,
)
from app.tcos.planner.runtime.intent import (
    PlannerIntent as RuntimePlannerIntent,
)
from app.tcos.planner.runtime.plan_candidate import (
    PlanCandidate as RuntimePlanCandidate,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext as RuntimePlanningContext,
)


def test_public_product_planning_contract_exports_core_types():
    assert PlannerIntent is RuntimePlannerIntent
    assert PlanCandidate is RuntimePlanCandidate
    assert PlanningContext is RuntimePlanningContext

    assert PlannerIntentName.CUSTOMER_REPLY == "customer_reply"

    assert ProductBusinessPlanBuilder is not None


def test_customer_service_product_planner_does_not_import_runtime():
    path = Path(
        "app/domains/customer_service/services/support/planning/"
        "customer_support_product_planner.py"
    )

    tree = ast.parse(path.read_text())

    forbidden = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        module = node.module or ""

        if module.startswith("app.tcos.planner.runtime"):
            forbidden.append(module)

    assert forbidden == []


def test_product_planning_contract_does_not_import_planner_runtime():
    path = Path("app/tcos/planner/product_planning/contracts.py")

    tree = ast.parse(path.read_text())

    forbidden = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        module = node.module or ""

        if module.startswith("app.tcos.planner.runtime"):
            forbidden.append(module)

    assert forbidden == []
