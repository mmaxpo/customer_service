# Feature: Basic Routing

## Spec
- **What it should do:** Automatically assign conversations to the right AI, agent, team, or queue via simple rules, with deterministic priority and a fallback.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/routing
- **Key entities:** Routing Rule, Assignment, Team, Agent, AI Handler, Queue
- **Core rules to check against:** Rules evaluated deterministically; rule priority/order defined; invalid targets cannot be assigned; assignment tenant-scoped; fallback routing must exist

## Acceptance criteria (from the v1 spec's "DONE" list)
- AI, human, team, round-robin, rule-based routing all work; default route exists
- Routing history recorded; tests cover conflicting/no-match rules

## Production success condition
> New conversations consistently reach an appropriate handler without manual assignment.

## Audit Result
_Filled in by `/audit-feature basic-routing`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Routing policies model: CustomerServiceRoutingPolicy (models/routing.py) with channel, intent, priority, strategy, candidate_assignee/team/queue_ids, priority_rank, is_fallback, is_active, filters
- Routing engine: CustomerServiceRoutingEngine (services/routing_engine/engine.py:54-118) evaluates policies deterministically, with fallback support
- Policy matching: RoutingPolicyMatcher checks channel/intent/priority/body keywords (routing_engine/matcher.py)
- Assignee selection: RoutingAssigneeSelector with round-robin/lowest-workload strategies (routing_engine/selector.py)
- Auto-assign endpoint: POST /tickets/{ticket_id}/auto-assign with first_available/round-robin strategies (inbox.py:193-204)
- Routing history: decisions recorded and returned in route_event() result (services/routing_policies.py:67-116)
- API endpoints: CRUD for routing policies via /workforce/routing-policies (workforce.py:321-380)
- Tenant isolation: user_id scoped throughout
- Tests: comprehensive including capacity, concurrency, team routing, unavailable agents, auto-assign idempotency (routing/test_*.py)

**Is it good enough?**
Mostly. Strengths:
- Deterministic policy evaluation with priority/order
- Fallback routing working
- Multiple assignment strategies (round-robin, lowest-load)
- Tenant isolation correct
- Comprehensive test coverage

Gaps vs spec:
- AI routing missing: spec requires "route to AI handler" but only agent/team/queue supported
- Priority rank not enforced: priority_rank field exists but not used in matching order (only channel/intent/priority used)
- Routing history not exposed in API: decisions logged but no GET endpoint to fetch routing history
- Invalid target validation not documented: no explicit check that assigned_to UUID is valid agent/team/queue
- Queue routing not tested: tests cover agents and teams but queue-based routing not explicitly tested

**Gaps / risks:**
1. AI routing missing: spec mentions routing to AI handler but implementation only supports agent/team/queue targets
2. Priority rank ignored: RoutingPolicyMatcher.matches() doesn't use priority_rank field for rule ordering
3. Routing history not exposed: decisions tracked but no API endpoint to retrieve routing decisions for a conversation
4. Target validation missing: no verification that assigned_to is valid before assignment
5. Queue routing untested: policy supports candidate_queue_ids but no tests for queue-based routing flow

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add AI handler routing: add ai_handler_id field to CustomerServiceRoutingPolicy model; support routing to AI in engine.py route_conversation()
- [ ] Enforce priority rank: modify RoutingPolicyMatcher.matches() to sort policies by priority_rank before evaluating
- [ ] Expose routing history: add GET /conversations/{conversation_id}/routing-history endpoint returning list of routing decisions
- [ ] Add target validation: in route_conversation(), verify assigned_to is valid agent/team/queue/ai-handler before returning assignment
- [ ] Add queue routing test: test_customer_service_queue_based_routing.py covering candidate_queue_ids assignment
- [ ] Add routing conflict test: test_customer_service_routing_policy_conflicts.py covering multiple matching policies, priority ordering
- [ ] Add no-match fallback test: test_customer_service_routing_no_match_fallback.py verifying fallback used when no policy matches
- [ ] Add AI handler integration test: test_customer_service_routing_to_ai_handler.py covering AI routing decision and execution 
