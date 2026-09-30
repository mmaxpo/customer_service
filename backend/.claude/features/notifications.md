# Feature: Notifications

## Spec
- **What it should do:** Important support, AI, approval, and SLA events generate appropriate notifications to the right recipient while avoiding noise.
- **Layer:** platform
- **Likely location (guess — verify, I don't have your repo):** app/platform/notifications (event generation, recipient resolution, delivery)
- **Key entities:** Notification, Notification Event, Recipient, Notification Preference, Delivery, Template
- **Core rules to check against:** Notifications tenant-scoped; recipient must be authorized; duplicate notifications prevented where appropriate; customer/internal notifications separated; failed delivery observable

## Acceptance criteria (from the v1 spec's "DONE" list)
- Required internal and customer notifications work; recipients correct
- Read/unread works; delivery failures tracked
- Internal and customer notifications separated; tenant isolation works
- Tests cover recipient and delivery behavior

## Production success condition
> The right person receives the right notification when meaningful customer-service work requires attention.

## Audit Result
_Filled in by `/audit-feature notifications`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- CustomerServiceNotification model (app/domains/customer_service/models/commercial.py): id, workspace_id, recipient_user_id, kind, entity_type, entity_id, payload, read_at, created_at. Index on (recipient_user_id, read_at).
- NotificationService (app/domains/customer_service/services/notifications.py): create(), create_if_uuid(), create_for_roles() with membership and tenant-scoping checks
- CommercialOperationsService methods (app/domains/customer_service/services/commercial_operations.py): create_notification(), list_notifications(unread_only), read_notification() with workspace isolation
- API endpoints (app/api/products/customer_service/commercial.py): POST /notifications (create), GET /notifications (list with unread_only param), POST /notifications/{id}/read
- Notification kinds auto-generated: "approval" (admins/owners), "mention" (mentioned users), "sla_risk" (assigned agent), from events handlers and services
- Recipient authorization enforced: create_notification checks membership exists and is active
- Read/unread state via read_at timestamp
- Test coverage in test_proactive_playbooks.py validating notification creation for proactive_alert kind

**Is it good enough?**
Partially. Core create/list/read operations exist with tenant isolation and basic recipient checks. However:
- **Architectural violation**: notifications implemented in product layer (customer_service), spec says platform layer. This prevents reuse across other products.
- No delivery mechanism (email, Slack, webhook, etc.) implemented — notifications are storage-only
- No notification preferences or user settings (users cannot opt-in/out or choose delivery channels)
- No notification templates or i18n
- No distinction between internal and customer notifications as spec requires
- No failed delivery tracking — if external delivery were added, no way to track failures
- Duplicate prevention exists only for create_for_roles(); create() and create_notification() can create duplicates
- Limited test coverage for edge cases (expired tokens, replay, cross-workspace leakage)

**Gaps / risks:**
1. **Boundary violation**: Feature should be platform layer but lives in product layer (domains/customer_service)
2. No email/Slack/webhook delivery backends implemented
3. No user notification preferences model or API
4. No customer vs. internal notification separation (both stored in same table)
5. No failed delivery or delivery_status field to track external delivery outcomes
6. create_notification() endpoint requires "cs.conversations.reply" permission but spec doesn't mandate this
7. No test for duplicate prevention when create() is called with identical parameters
8. No test for cross-workspace isolation (can a user in workspace A receive notifications from workspace B?)
9. Notification kinds are ad-hoc (kind is string); no schema for valid kinds

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **CRITICAL**: Migrate notifications from product layer to platform layer — create app/platform/notifications/service.py and move NotificationService there, then make customer_service import from platform
- [ ] Add DeliveryStatus enum (pending, sent, failed, bounced) to CustomerServiceNotification model and add delivery_status column
- [ ] Add NotificationPreference model (app/platform/notifications/models.py) with fields: user_id, workspace_id, notification_kind, delivery_channel (email/slack/inapp), enabled, updated_at
- [ ] Implement PlatformNotificationService.send_notification() to dispatch based on preferences and delivery_channel (currently only in-app storage)
- [ ] Add notification_type field to CustomerServiceNotification to distinguish "internal" vs "customer" (both currently mixed)
- [ ] Add unique constraint to CustomerServiceNotification table to prevent duplicates: (workspace_id, recipient_user_id, kind, entity_type, entity_id)
- [ ] Add test in tests/customer_service/test_notification_preferences_http.py for user prefs CRUD and isolation
- [ ] Add test in tests/customer_service/test_notification_delivery.py for duplicate prevention on create()
- [ ] Add test in tests/customer_service/test_notification_isolation.py for cross-workspace boundary (verify user in workspace A cannot receive workspace B notifications) 
