# Mission Board V1 Finish Checklist

Mission Board V1 is not an endless feature.  
It is finished when the merchant can observe a real AI mission serving a real customer.

## Goal

Builder → Inbox → Runtime → Mission Board → Customer reply

## Definition of Done

A merchant can:

1. Create or load an Order Status mission.
2. Run it from Inbox/customer conversation.
3. See AI working in Inbox.
4. Open Mission Board from that execution.
5. See runtime status and run identity.
6. See mission/session context.
7. See graph nodes reflect runtime progress.
8. Confirm the customer received a reply.

## Current Status

### Builder

- [x] Build workflow
- [x] Save/load workflow template
- [x] Open Mission Board

### Mission Board

- [x] Mission Board route
- [x] Mission Board launcher
- [x] Mission workspace layout
- [x] Mission compiler foundation
- [x] Mission graph
- [x] Entity inspector
- [x] Relationship inspector
- [x] Mission run model
- [x] Runtime status summary
- [x] Mission session context
- [x] Load by runId
- [x] Load by templateId
- [x] Receive conversationId

### Inbox

- [x] Link workflow execution to Mission Board
- [ ] Show clear AI Working state
- [ ] Show Observe Mission button on active workflow execution

### Runtime Visualization

- [ ] Highlight running mission node
- [ ] Highlight completed mission node
- [ ] Highlight failed mission node

### Manual Test

- [ ] Create Order Status mission
- [ ] Run from Inbox
- [ ] Open Mission Board
- [ ] Confirm runtime streams
- [ ] Confirm final reply reaches customer

## Remaining Patch Budget

Maximum 6 patches:

1. Inbox AI Working state
2. Observe Mission CTA
3. Runtime status overlay on Mission graph
4. Mission graph maps runtime node status
5. Manual test helper/checklist UI or docs
6. Final cleanup/polish

After these patches, stop feature development and manually test V1.
