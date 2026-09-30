set -e

python - <<'PY'
import asyncio

from app.tcos.cognitive import CognitiveRuntime
from app.runtime.tools import build_tools


async def main():
    tools = build_tools()
    try:
        ctx = type("Ctx", (), {"tools": tools})()

        session = await CognitiveRuntime().execute_goal_runtime(
            goal="Reply to this customer: Where is my order?",
            ctx=ctx,
        )

        data = session.model_dump(mode="json")
        runtime_result = (data.get("execution_session") or {}).get("runtime_result") or {}

        print("=== COGNITIVE STATUS ===")
        print(data["status"])

        print("\n=== EVENTS ===")
        for event in data["events"]:
            print(event["type"], event["payload"])

        print("\n=== RUNTIME RESULT ===")
        print(runtime_result)

        print("\n=== FINAL ANSWER ===")
        print(runtime_result.get("answer"))
    finally:
        await tools.aclose()


asyncio.run(main())
PY
