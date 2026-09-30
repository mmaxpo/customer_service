from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    CustomerServiceShopifyConnection,
    CustomerServiceShopifyOrderCache,
)
from app.domains.customer_service.services.shopify_provider_installation import (
    ShopifyProviderInstallationProjector,
)
from app.main import app
from app.models.models import User
from app.api.auth import get_current_user


SHOP_DOMAIN = "tajeran-product-planning-test.myshopify.com"


class FakeUser:
    def __init__(self, user_id: UUID):
        self.id = user_id


class ProductPlanningAgentResponse:
    """Minimal Responses-compatible result for the HTTP contract."""

    def __init__(
        self,
        output_text: str,
    ) -> None:
        self.output = []
        self.output_text = output_text
        self.usage = None
        self.model = "product-planning-http-test"


class ProductPlanningAgentLLM:
    """
    Deterministic agent LLM for the Product-planning HTTP contract.

    The test owns Product planning, semantic capability execution,
    provider resolution, Runtime execution, and HTTP wiring. It must
    not depend on external model credits or response randomness.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def respond(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)

        return ProductPlanningAgentResponse(
            "Order #1001 is fulfilled. "
            "UPS tracking number 1Z999AA10123456784."
        )


async def _seed_user(user_id: UUID) -> None:
    async with SessionLocal() as db:
        if await db.get(User, user_id) is None:
            db.add(
                User(
                    id=user_id,
                    email=f"product-planning-{user_id}@example.com",
                    hashed_password="test-only",
                    full_name="Product Planning HTTP Test",
                    is_active=True,
                )
            )
            await db.commit()


async def _seed_known_order(user_id: UUID) -> None:
    async with SessionLocal() as db:
        if await db.get(User, user_id) is None:
            db.add(
                User(
                    id=user_id,
                    email=f"product-planning-{user_id}@example.com",
                    hashed_password="test-only",
                    full_name="Product Planning HTTP Test",
                    is_active=True,
                )
            )

        result = await db.execute(
            select(CustomerServiceShopifyConnection).where(
                CustomerServiceShopifyConnection.user_id == user_id,
                CustomerServiceShopifyConnection.status == "active",
            )
        )
        connection = result.scalar_one_or_none()

        if connection is None:
            connection = CustomerServiceShopifyConnection(
                user_id=user_id,
                shop_domain=SHOP_DOMAIN,
                access_token_encrypted="plain:test-token",
                status="active",
            )
            db.add(connection)
            await db.flush()

        await ShopifyProviderInstallationProjector(db).project_verified(
            user_id=user_id,
            connection_id=connection.id,
            shop_domain=connection.shop_domain,
        )

        result = await db.execute(
            select(CustomerServiceShopifyOrderCache).where(
                CustomerServiceShopifyOrderCache.user_id == user_id,
                CustomerServiceShopifyOrderCache.order_name == "#1001",
            )
        )
        cached_order = result.scalar_one_or_none()

        payload = {
            "id": "1001",
            "name": "#1001",
            "email": "customer@example.com",
            "financial_status": "paid",
            "fulfillment_status": "fulfilled",
            "total_price": "89.00",
            "currency": "USD",
            "created_at": "2026-07-01T10:00:00Z",
            "fulfillments": [
                {
                    "tracking_number": "1Z999AA10123456784",
                    "tracking_company": "UPS",
                    "tracking_url": (
                        "https://www.ups.com/track?tracknum=1Z999AA10123456784"
                    ),
                    "shipment_status": "in_transit",
                }
            ],
            "shipping_address": {
                "city": "New York",
                "province": "NY",
                "country": "United States",
                "zip": "10001",
            },
        }

        if cached_order is None:
            db.add(
                CustomerServiceShopifyOrderCache(
                    user_id=user_id,
                    shop_domain=SHOP_DOMAIN,
                    order_id="1001",
                    order_name="#1001",
                    customer_email="customer@example.com",
                    payload=payload,
                )
            )
        else:
            cached_order.shop_domain = SHOP_DOMAIN
            cached_order.order_id = "1001"
            cached_order.customer_email = "customer@example.com"
            cached_order.payload = payload

        await db.commit()


@pytest.mark.asyncio
async def test_runtime_http_product_planning_clarifies_missing_order_reference():
    user_id = uuid4()
    await _seed_user(user_id)

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/tcos/execute-goal-runtime",
                json={
                    "goal": "My order hasn't arrived. Check it for me.",
                    "thread_id": str(uuid4()),
                    "strict": True,
                },
            )

        assert response.status_code == 200

        session = response.json()["session"]
        planner = session["planner_session"]

        assert session["status"] == "completed"
        assert planner["status"] == "clarification_required"

        clarification = planner["clarification"]

        assert clarification["reason_code"] == "missing_order_ref"
        assert clarification["missing_fields"] == ["order_ref"]
        assert clarification["metadata"]["support_intent"] == "shipping"

        assert planner["business_plan"] is None
        assert planner["verification_result"] is None
        assert planner["compilation"] is None
        assert session["execution_session"] is None

        planner_event_types = {event["type"] for event in planner["events"]}

        assert "PlanningClarificationRequired" in planner_event_types
        assert "VerificationCompleted" not in planner_event_types
        assert "BusinessPlanCreated" not in planner_event_types
        assert "CompilationSucceeded" not in planner_event_types

        cognitive_event_types = {event["type"] for event in session["events"]}

        assert "CognitiveClarificationRequired" in cognitive_event_types
        assert "CognitiveSessionCompleted" in cognitive_event_types

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_runtime_http_product_planning_executes_semantic_order_lookup():
    user_id = uuid4()
    await _seed_known_order(user_id)

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user_id)

    previous_tools = getattr(
        app.state,
        "tools",
        None,
    )

    scenario_agent_llm = ProductPlanningAgentLLM()

    if previous_tools is None:
        from types import SimpleNamespace

        test_tools = SimpleNamespace(
            agent_llm=scenario_agent_llm,
        )
    else:
        test_tools = previous_tools
        test_tools.agent_llm = scenario_agent_llm

    app.state.tools = test_tools

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/tcos/execute-goal-runtime",
                json={
                    "goal": ("Reply to this customer: Where is my order #1001?"),
                    "thread_id": str(uuid4()),
                    "strict": True,
                },
            )

        assert response.status_code == 200

        session = response.json()["session"]
        planner = session["planner_session"]

        assert session["status"] == "completed"
        assert planner["status"] == "compiled"
        assert planner["clarification"] is None

        candidate = planner["selected_candidate"]

        assert candidate["source"] == "customer_service_product_planner"
        assert candidate["metrics"]["product_id"] == "customer_service"
        assert candidate["metrics"]["support_intent"] == "shipping"
        assert candidate["metrics"]["order_ref"] == "#1001"

        business_plan = planner["business_plan"]
        business_plan_text = str(business_plan)

        assert "ecommerce.orders.get" in business_plan_text
        assert "shopify.get_order" not in business_plan_text

        lookup_task = next(
            task for task in business_plan["tasks"] if task["id"] == "lookup_order"
        )

        assert (
            lookup_task["required_capabilities"][0]["capability_id"]
            == "ecommerce.orders.get"
        )
        assert lookup_task["metadata"]["operation"]["inputs"] == ["order_ref"]
        assert lookup_task["metadata"]["operation"]["outputs"] == ["commerce_order"]

        verification = planner["verification_result"]

        assert verification["passed"] is True
        assert verification["issues"] == []
        assert verification["confidence"]["overall"] == 1.0

        compilation = planner["compilation"]

        assert compilation["ok"] is True

        graph = compilation["execution_graph"]

        lookup_node = next(
            node for node in graph["nodes"] if node["id"] == "lookup_order"
        )

        assert lookup_node["node_type"] == "capability.invoke"
        assert lookup_node["config"]["capability_id"] == ("ecommerce.orders.get")
        assert lookup_node["config"]["input_from"] == "vars"
        assert lookup_node["config"]["input_key"] == "order_ref"
        assert lookup_node["config"]["save_as"] == "commerce_order"

        execution = session["execution_session"]

        assert execution is not None
        assert execution["status"] == "completed"

        runtime_result = execution["runtime_result"]
        runtime_meta = runtime_result["meta"]

        assert runtime_meta["status"] == "ok"

        # Prove runtime.agent_custom actually executed rather than a
        # Product-specific deterministic shortcut.
        assert len(scenario_agent_llm.calls) == 1

        final_vars = runtime_meta["final_state"]["vars"]

        assert final_vars["order_ref"] == "#1001"
        assert "commerce_order" in final_vars
        assert "shopify_order" not in final_vars

        commerce_order = final_vars["commerce_order"]

        assert commerce_order["order_name"] == "#1001"
        assert commerce_order["summary"]["order_name"] == "#1001"
        assert commerce_order["summary"]["tracking_number"] == "1Z999AA10123456784"
        assert commerce_order["summary"]["carrier"] == "UPS"

        capability_result = final_vars["commerce_order_capability_result"]

        assert capability_result["status"] == "ok"
        assert capability_result["capability_id"] == ("ecommerce.orders.get")

        metadata = capability_result["metadata"]

        assert metadata["resolved_capability_id"] == ("ecommerce.orders.get")
        assert metadata["selected_provider_id"] == "shopify"
        assert metadata["provider_ref"] == "shopify.get_order"
        assert metadata["runtime_node_type"] == "capability.invoke"

        execution_outcome = metadata["execution_outcome"]

        assert execution_outcome["status"] == "succeeded"
        assert execution_outcome["ok"] is True
        assert execution_outcome["selected_provider_id"] == "shopify"
        assert execution_outcome["provider_ref"] == "shopify.get_order"
        assert execution_outcome["fallback_used"] is False

        assert runtime_result["answer"] == final_vars["answer"]
        assert "1001" in runtime_result["answer"]
        assert "fulfilled" in runtime_result["answer"].lower()
        assert "1Z999AA10123456784" in runtime_result["answer"]
        assert "UPS" in runtime_result["answer"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)

        if previous_tools is None:
            if hasattr(app.state, "tools"):
                delattr(app.state, "tools")
        else:
            app.state.tools = previous_tools
