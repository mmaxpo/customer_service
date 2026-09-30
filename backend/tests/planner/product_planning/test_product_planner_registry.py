from __future__ import annotations

import pytest

from app.tcos.planner.product_planning import (
    ProductPlanner,
    ProductPlannerNotFoundError,
    ProductPlannerRegistry,
    build_default_product_planner_registry,
)


class ExampleProductPlanner:
    @property
    def product_id(self) -> str:
        return "example"

    def plan(
        self,
        *,
        intent,
        context=None,
    ):
        from app.tcos.planner.product_planning import (
            ProductPlanningResult,
        )

        return ProductPlanningResult(
            product_id=self.product_id,
            claimed=False,
        )


class InvalidProductPlanner:
    product_id = "invalid"


def test_product_planner_protocol_runtime_check():
    assert isinstance(
        ExampleProductPlanner(),
        ProductPlanner,
    )

    assert not isinstance(
        InvalidProductPlanner(),
        ProductPlanner,
    )


def test_register_and_resolve_normalizes_product_id():
    registry = ProductPlannerRegistry()
    planner = ExampleProductPlanner()

    registry.register(planner)

    assert registry.resolve(" EXAMPLE ") is planner
    assert registry.contains("Example")


def test_duplicate_registration_is_rejected():
    registry = ProductPlannerRegistry()

    registry.register(ExampleProductPlanner())

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(ExampleProductPlanner())


def test_invalid_planner_is_rejected():
    registry = ProductPlannerRegistry()

    with pytest.raises(
        TypeError,
        match="ProductPlanner",
    ):
        registry.register(InvalidProductPlanner())


@pytest.mark.parametrize(
    "product_id",
    [
        "",
        "   ",
    ],
)
def test_blank_product_id_is_rejected(product_id):
    registry = ProductPlannerRegistry()

    with pytest.raises(
        ValueError,
        match="product_id is required",
    ):
        registry.resolve(product_id)


def test_unknown_product_error_is_stable():
    registry = ProductPlannerRegistry()

    with pytest.raises(
        ProductPlannerNotFoundError,
        match="product planner not found for missing",
    ):
        registry.resolve("Missing")


def test_registered_product_ids_are_sorted():
    class ZetaPlanner(ExampleProductPlanner):
        @property
        def product_id(self):
            return "zeta"

    class AlphaPlanner(ExampleProductPlanner):
        @property
        def product_id(self):
            return "alpha"

    registry = ProductPlannerRegistry()

    registry.register(ZetaPlanner())
    registry.register(AlphaPlanner())

    assert registry.registered_product_ids() == (
        "alpha",
        "zeta",
    )


def test_default_registry_is_product_neutral():
    registry = build_default_product_planner_registry()

    assert registry.registered_product_ids() == ()
