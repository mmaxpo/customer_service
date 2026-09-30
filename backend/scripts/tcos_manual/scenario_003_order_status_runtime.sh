set -e

python - <<'PY'
import asyncio
import uuid

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

DEMO_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SHOP_DOMAIN = "tajeran-support-dev.myshopify.com"


async def seed(db):
    user = await db.get(User, DEMO_USER_ID)
    if user is None:
        user = User(
            id=DEMO_USER_ID,
            email="scenario-003@example.com",
            hashed_password="manual-test",
            full_name="Scenario 003 User",
            is_active=True,
        )
        db.add(user)

    result = await db.execute(
        select(CustomerServiceShopifyConnection).where(
            CustomerServiceShopifyConnection.user_id == DEMO_USER_ID,
            CustomerServiceShopifyConnection.status == "active",
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        db.add(
            CustomerServiceShopifyConnection(
                user_id=DEMO_USER_ID,
                shop_domain=SHOP_DOMAIN,
                access_token_encrypted="plain:manual-test-token",
                status="active",
            )
        )

    result = await db.execute(
        select(CustomerServiceShopifyOrderCache).where(
            CustomerServiceShopifyOrderCache.user_id == DEMO_USER_ID,
            CustomerServiceShopifyOrderCache.order_name == "#1001",
        )
    )
    cached_order = result.scalar_one_or_none()
    if cached_order is None:
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
                    "created_at": "2026-07-01T10:00:00Z",
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


async def main():
    tools = build_tools()
    try:
        async with SessionLocal() as db:
            await seed(db)

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

            goal = "Reply to this customer: Where is my order #1001?"

            session = await build_application_cognitive_runtime().execute_goal_runtime(
                goal=goal,
                ctx=ctx,
                user_id=str(DEMO_USER_ID),
            )

        data = session.model_dump(mode="json")
        runtime_result = (data.get("execution_session") or {}).get("runtime_result") or {}
        planner = data.get("planner_session") or {}

        print("=== GOAL ===")
        print(goal)

        print("\n=== COGNITIVE STATUS ===")
        print(data["status"])

        print("\n=== EVENTS ===")
        for event in data["events"]:
            print(event["type"], event["payload"])

        print("\n=== SELECTED CANDIDATE ===")
        print(planner.get("selected_candidate"))

        print("\n=== RUNTIME RESULT ===")
        print(runtime_result)

        print("\n=== FINAL ANSWER ===")
        print(runtime_result.get("answer"))
    finally:
        await tools.aclose()


asyncio.run(main())
PY
