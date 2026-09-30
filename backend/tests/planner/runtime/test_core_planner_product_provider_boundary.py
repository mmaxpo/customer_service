from pathlib import Path


CORE_PLANNER_ROOT = Path("app/tcos/planner")

ALLOWED_PRODUCT_CONTRACT_AREA = (
    CORE_PLANNER_ROOT / "product_planning"
)

# General customer-reply compatibility remains temporarily.
# Order/provider planning is already Product-owned.
FORBIDDEN = (
    "customer_service.order_status",
    "customer_service.customer_reply",
    "customer_service.extract_order_ref",
    "shopify.get_order",
)


def test_core_planner_has_no_order_or_provider_planning_knowledge():
    hits: list[tuple[str, str]] = []

    for path in CORE_PLANNER_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue

        if path.is_relative_to(
            ALLOWED_PRODUCT_CONTRACT_AREA
        ):
            continue

        text = path.read_text(
            encoding="utf-8",
        )

        for term in FORBIDDEN:
            if term in text:
                hits.append(
                    (
                        path.as_posix(),
                        term,
                    )
                )

    assert hits == []
