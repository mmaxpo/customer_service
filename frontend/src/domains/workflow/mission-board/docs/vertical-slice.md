# Mission Board Vertical Slice

Goal:

Builder → Inbox/customer chat → Runtime job → Mission Board proof

## Slice 1: Order Status Mission

1. Build workflow in `/app/workflows/builder`
2. Save or load Order Status Mission
3. Customer sends chat message: "Where is my order #1001?"
4. Inbox/customer-service starts workflow runtime
5. Runtime events stream node execution
6. Mission Board opens that mission/run
7. Admin can inspect:
   - mission graph
   - selected agent/tool
   - runtime events
   - variables/state
   - final customer reply

## Product Rule

Builder designs the mission.
Inbox triggers the mission.
Runtime executes the mission.
Mission Board explains the mission.
