set -e

python - <<'PY'
from app.tcos.cognitive import CognitiveRuntime

goal = "Reply to this customer: Where is my order?"

session = CognitiveRuntime().execute_goal(goal=goal)

print("=== COGNITIVE STATUS ===")
print(session.status)

print("\n=== EVENTS ===")
for event in session.events:
    print(event.type, event.payload)

print("\n=== PLANNER SESSION ===")
print(session.planner_session)

print("\n=== EXECUTION SESSION ===")
print(session.execution_session)

print("\n=== METRICS ===")
print(session.metrics)
PY
