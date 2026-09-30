# Feature: Analytics

## Spec
- **What it should do:** Simple, trustworthy operational dashboard for support, AI, and team performance over a selected time range.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/analytics (metric aggregation)
- **Key entities:** Conversation volume, open/resolution counts, first-response/resolution time, AI handling/escalation/failure rate, action success rate, resolution rate, agent workload
- **Core rules to check against:** Metrics must have defined meanings; time windows consistent; AI metrics distinguish generated response from successful resolution; missing data must not silently become misleading zeros

## Acceptance criteria (from the v1 spec's "DONE" list)
- Support, AI, and team metrics all work; date range works
- Metrics match source data; performance acceptable; tests verify calculations

## Production success condition
> Merchant can open Analytics and trust that the displayed numbers accurately represent what happened in support.

## Audit Result
_Filled in by `/audit-feature analytics`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Analytics service: AnalyticsService (services/analytics.py) with get_summary(), workload(), workload_report()
- Summary schema: CustomerServiceAnalytics (schemas/analytics.py) with total_customers, total_conversations, ticket counts by status/priority, open_sla_breaches
- API endpoints: GET /analytics (summary), GET /analytics/workload (by assignee), GET /analytics/workload-report (queues/teams/agents)
- Workload metrics: counts of open/pending tickets per agent/team/queue (repositories/analytics.py)
- Business learning analytics: endpoints with time window support (hours_lookback parameter)
- Tenant isolation: user_id scoped throughout
- Tests: analytics calculation tests, business value tests (test_customer_service_analytics.py)

**Is it good enough?**
Partially. Strengths:
- Basic counts (conversations, tickets, SLA breaches) work
- Workload visibility by agent/team/queue
- Tenant isolation correct

Gaps vs spec:
- No date range filtering: summary has no start_date/end_date parameters for time range selection
- Missing response/resolution time metrics: no avg/p95 first-response or resolution times
- No AI metrics: no AI handling rate, escalation rate, failure rate
- No success rates: no action success rate or resolution rate by channel/priority
- No agent performance: only workload visible, not resolution rate/quality metrics
- Missing metric definitions: no documented meanings for edge cases (what counts as "handled"?)
- No dashboard UI: only raw API endpoints, no merchant-facing dashboard

**Gaps / risks:**
1. Date range missing: summary can't filter by time period; merchants see all-time only
2. No AI performance metrics: can't see how often AI handled vs escalated
3. No resolution/response time metrics: can't see SLA compliance performance visually
4. No agent quality metrics: workload visible but not effectiveness/resolution rate
5. Missing metric documentation: edge cases (reopened tickets, partial AI handling) not defined

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add date range filtering: add start_date, end_date parameters to GET /analytics in analytics.py; modify repository queries to filter by date range
- [ ] Add response time metrics: add avg_first_response_minutes, p95_first_response_minutes to CustomerServiceAnalytics schema
- [ ] Add resolution time metrics: add avg_resolution_minutes, p95_resolution_minutes to schema
- [ ] Add AI metrics: add ai_handled_count, ai_escalated_count, ai_failure_count to schema; implement calculation in AnalyticsService
- [ ] Add resolution rate metrics: add resolution_rate_pct, channels_breakdown to schema with counts by channel
- [ ] Add agent performance: add agent_performance array to workload_report with resolution_rate, avg_response_time per agent
- [ ] Document metric definitions: create docs/ANALYTICS_METRICS.md defining each metric, edge cases, calculation method
- [ ] Add dashboard UI: create /analytics dashboard page showing summary + charts for trends
- [ ] Add analytics validation tests: test_customer_service_analytics_date_range.py verifying filters work; test calculations match source
- [ ] Add metric audit trail: log each analytics query with parameters for audit/compliance 
