# Tajeran Frontend Architecture

Frontend priority is Inbox first.

Backend customer-service v1 is frozen enough for frontend work.

Main frontend rule:

Do not connect random components directly to random backend endpoints.

Each page must have:
- one product purpose
- one primary data flow
- typed API client
- separated components
- separated hooks
- documented endpoint usage

## First Product Screen

`/app/inbox`

This is the product center.

## Inbox API Loading Order

1. `GET /api/customer-service/inbox/`
2. `GET /api/customer-service/conversations/{conversation_id}`
3. `GET /api/customer-service/conversations/{conversation_id}/intelligence/snapshot`
4. `GET /api/customer-service/conversations/{conversation_id}/workspace-recommendations`

Lazy-load later:
- timeline
- context
- workflow executions
- customer activity
- customer 360

####################################
Here’s our remaining roadmap

✅ Completed

* Mission compiler
* Mission model
* Mission run
* Mission session
* Runtime bridge
* Template loading
* Run loading
* Conversation context
* Runtime status
* Mission story
* AI Operations Center naming
* Live execution strip foundation