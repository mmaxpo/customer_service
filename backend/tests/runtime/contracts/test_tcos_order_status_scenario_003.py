import uuid

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import User
from app.runtime_services import build_application_runtime_services
from app.runtime.tools import build_tools
from app.cognitive_runtime import build_application_cognitive_runtime
from app.domains.customer_service.models import (
    CustomerServiceShopifyConnection,
    CustomerServiceShopifyOrderCache,
)
from app.domains.customer_service.services.shopify_provider_installation import (
    ShopifyProviderInstallationProjector,
)

DEMO_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SHOP_DOMAIN = "tajeran-support-dev.myshopify.com"


class Scenario003AgentResponse:
    """Minimal Responses-compatible result for Scenario 003."""

    def __init__(
        self,
        output_text: str,
    ) -> None:
        self.output = []
        self.output_text = output_text
        self.usage = None
        self.model = "scenario-003-test"


class Scenario003AgentLLM:
    """
    Deterministic agent LLM for the runtime contract.

    Scenario 003 validates Product planning, semantic capability
    execution, provider resolution, and Runtime data flow. It must not
    depend on external API credits or model randomness.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def respond(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)

        return Scenario003AgentResponse(
            "Order #1001 is fulfilled. "
            "UPS tracking number 1Z999AA10123456784."
        )


async def seed_scenario_003(db):
    user = await db.get(User, DEMO_USER_ID)
    if user is None:
        db.add(
            User(
                id=DEMO_USER_ID,
                email="scenario-003@example.com",
                hashed_password="manual-test",
                full_name="Scenario 003 User",
                is_active=True,
            )
        )

    result = await db.execute(
        select(CustomerServiceShopifyConnection).where(
            CustomerServiceShopifyConnection.user_id == DEMO_USER_ID,
            CustomerServiceShopifyConnection.status == "active",
        )
    )
    connection = result.scalar_one_or_none()

    if connection is None:
        connection = CustomerServiceShopifyConnection(
            user_id=DEMO_USER_ID,
            shop_domain=SHOP_DOMAIN,
            access_token_encrypted=(
                "plain:manual-test-token"
            ),
            status="active",
        )
        db.add(connection)
        await db.flush()

    await ShopifyProviderInstallationProjector(
        db
    ).project_verified(
        user_id=DEMO_USER_ID,
        connection_id=connection.id,
        shop_domain=connection.shop_domain,
    )

    result = await db.execute(
        select(CustomerServiceShopifyOrderCache).where(
            CustomerServiceShopifyOrderCache.user_id == DEMO_USER_ID,
            CustomerServiceShopifyOrderCache.order_name == "#1001",
        )
    )
    if result.scalar_one_or_none() is None:
        db.add(
            CustomerServiceShopifyOrderCache(
                user_id=DEMO_USER_ID,
                shop_domain=SHOP_DOMAIN,
                order_id="1001",
                order_name="#1001",
                customer_email="customer@example.com",
                payload={
                    "id": "1001",
                    "name": "#1001",
                    "email": "customer@example.com",
                    "financial_status": "paid",
                    "fulfillment_status": "fulfilled",
                    "total_price": "89.00",
                    "currency": "USD",
                    "fulfillments": [
                        {
                            "tracking_number": "1Z999AA10123456784",
                            "tracking_company": "UPS",
                            "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
                            "shipment_status": "in_transit",
                        }
                    ],
                    "shipping_address": {
                        "city": "New York",
                        "province": "NY",
                        "country": "United States",
                        "zip": "10001",
                    },
                },
            )
        )

    await db.commit()


@pytest.mark.asyncio
async def test_tcos_scenario_003_order_status_runtime_contract():
    tools = build_tools()
    scenario_agent_llm = Scenario003AgentLLM()
    tools.agent_llm = scenario_agent_llm

    try:
        async with SessionLocal() as db:
            await seed_scenario_003(db)

            services = build_application_runtime_services(
                db=db,
                tools=tools,
                user_id=DEMO_USER_ID,
            )

            ctx = type(
                "Ctx",
                (),
                {
                    "tools": tools,
                    "db": db,
                    "services": services,
                    "user_id": DEMO_USER_ID,
                },
            )()

            session = await build_application_cognitive_runtime().execute_goal_runtime(
                goal="Reply to this customer: Where is my order #1001?",
                ctx=ctx,
                user_id=str(DEMO_USER_ID),
            )

    finally:
        await tools.aclose()

    data = session.model_dump(mode="json")
    runtime_result = (data.get("execution_session") or {}).get("runtime_result") or {}
    planner = data.get("planner_session") or {}
    candidate = planner.get("selected_candidate") or {}
    answer = runtime_result.get("answer") or ""

    assert data["status"] == "completed"
    assert runtime_result["meta"]["status"] == "ok"

    # The generic agent node must execute normally. This prevents the
    # removed Product-specific deterministic shortcut from returning.
    assert len(scenario_agent_llm.calls) == 1

    assert candidate["id"] == "generated_customer_service_order_status"
    assert (
        candidate["metrics"]["selected_capability"] == "customer_service.order_status"
    )

    assert "1001" in answer
    assert "fulfilled" in answer.lower()
    assert "1Z999AA10123456784" in answer
    assert "UPS" in answer

    business_plan = planner["business_plan"]
    business_plan_text = str(business_plan)

    assert "ecommerce.orders.get" in business_plan_text
    assert "shopify.get_order" not in business_plan_text

    compilation = planner["compilation"]
    assert compilation["ok"] is True

    lookup_node = next(
        node
        for node in compilation["execution_graph"]["nodes"]
        if node["id"] == "lookup_order"
    )

    assert lookup_node["node_type"] == "capability.invoke"
    assert lookup_node["config"]["capability_id"] == "ecommerce.orders.get"
    assert lookup_node["config"]["save_as"] == "commerce_order"

    final_state = runtime_result["meta"]["final_state"]
    final_vars = final_state["vars"]

    assert final_vars["order_ref"] == "#1001"
    assert "commerce_order" in final_vars
    assert "shopify_order" not in final_vars

    commerce_order = final_vars["commerce_order"]

    assert commerce_order["order_name"] == "#1001"
    assert commerce_order["summary"]["order_name"] == "#1001"
    assert commerce_order["summary"]["tracking_number"] == "1Z999AA10123456784"
    assert commerce_order["summary"]["carrier"] == "UPS"

    capability_result = final_vars[
        "commerce_order_capability_result"
    ]

    assert capability_result["status"] == "ok"
    assert capability_result["capability_id"] == "ecommerce.orders.get"

    metadata = capability_result["metadata"]

    assert metadata["resolved_capability_id"] == "ecommerce.orders.get"
    assert metadata["selected_provider_id"] == "shopify"
    assert metadata["provider_ref"] == "shopify.get_order"
    assert metadata["runtime_node_type"] == "capability.invoke"

    execution_outcome = metadata["execution_outcome"]

    assert execution_outcome["status"] == "succeeded"
    assert execution_outcome["ok"] is True
    assert execution_outcome["selected_provider_id"] == "shopify"
    assert execution_outcome["provider_ref"] == "shopify.get_order"
    assert execution_outcome["fallback_used"] is False

    assert final_vars["answer"] == answer
