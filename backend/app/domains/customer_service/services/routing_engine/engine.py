from __future__ import annotations

from sqlalchemy import text
from app.domains.customer_service.repositories.routing_policies import (
    CustomerServiceRoutingPolicyRepository,
)
from app.domains.customer_service.repositories.tickets import (
    TicketRepository,
)
from app.domains.customer_service.repositories.agents import (
    CustomerServiceAgentRepository,
)
from app.domains.customer_service.repositories.teams import (
    CustomerServiceTeamRepository,
)
from app.domains.customer_service.repositories.queues import (
    CustomerServiceQueueRepository,
)
from app.domains.customer_service.repositories.analytics import (
    AnalyticsRepository,
)
from app.domains.customer_service.services.assignment import (
    AssignmentService,
)
from app.domains.customer_service.services.routing_engine.matcher import (
    RoutingPolicyMatcher,
)
from app.domains.customer_service.services.routing_engine.selector import (
    RoutingAssigneeSelector,
)
from app.domains.customer_service.services.best_agent_selector import (
    BestAgentSelector,
)


class CustomerServiceRoutingEngine:
    def __init__(self, db):
        self.db = db

        self.policy_repo = CustomerServiceRoutingPolicyRepository(db)

        self.ticket_repo = TicketRepository(db)

        self.analytics_repo = AnalyticsRepository(db)

        self.agent_repo = CustomerServiceAgentRepository(db)

        self.team_repo = CustomerServiceTeamRepository(db)

        self.queue_repo = CustomerServiceQueueRepository(db)

        self.selector = RoutingAssigneeSelector(self.analytics_repo)

    async def route_conversation(
        self,
        *,
        user_id,
        conversation_id,
        channel: str,
        body: str,
        intent: str | None,
        priority: str | None,
    ):

        ticket = await self.ticket_repo.get_by_conversation(
            user_id,
            conversation_id,
        )

        if ticket is None:
            return None

        policies = await self.policy_repo.list_matching(
            user_id=user_id,
            channel=channel,
            intent=intent,
            priority=priority,
        )

        matched_policy = None
        fallback_policy = None

        for policy in policies:
            if policy.is_fallback and fallback_policy is None:
                fallback_policy = policy

            if RoutingPolicyMatcher.matches(
                policy=policy,
                channel=channel,
                intent=intent,
                priority=priority,
                body=body,
            ):
                matched_policy = policy
                break

        if matched_policy is None:
            matched_policy = fallback_policy

        if matched_policy is None:
            return None

        lock_key = f"cs_routing_policy:{user_id}:{matched_policy.id}"
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": lock_key},
        )

        candidate_assignee_ids = [
            str(item) for item in matched_policy.candidate_assignee_ids
        ]

        max_open_tickets_by_assignee = {}

        known_candidate_profiles = await self.agent_repo.list_by_agent_user_ids(
            user_id=user_id,
            agent_user_ids=candidate_assignee_ids,
        )

        known_profile_ids = {
            str(agent.agent_user_id) for agent in known_candidate_profiles
        }

        available_known_profile_ids = {
            str(agent.agent_user_id)
            for agent in known_candidate_profiles
            if agent.status == "active" and agent.availability == "available"
        }

        candidate_assignee_ids = [
            candidate_id
            for candidate_id in candidate_assignee_ids
            if candidate_id not in known_profile_ids
            or candidate_id in available_known_profile_ids
        ]

        for agent in known_candidate_profiles:
            assignee_id = str(agent.agent_user_id)
            if assignee_id in candidate_assignee_ids:
                max_open_tickets_by_assignee[assignee_id] = agent.max_open_tickets

        team_ids = [
            str(item)
            for item in getattr(matched_policy, "candidate_team_ids", []) or []
        ]

        queue_ids = [
            str(item)
            for item in getattr(matched_policy, "candidate_queue_ids", []) or []
        ]

        if queue_ids:
            queues = await self.queue_repo.list_by_ids(
                user_id=user_id,
                queue_ids=queue_ids,
            )
            for queue in queues:
                if queue.team_id is not None:
                    team_id = str(queue.team_id)
                    if team_id not in team_ids:
                        team_ids.append(team_id)

        if team_ids:
            profile_filters = (matched_policy.filters or {}).get("agent_profile") or {}

            for team_id in team_ids:
                selected_team_agent = await BestAgentSelector(self.db).select_for_team(
                    user_id=user_id,
                    team_id=team_id,
                    required_skills=profile_filters.get("skills") or [],
                    channel=channel,
                    language=(profile_filters.get("languages") or [None])[0],
                )

                if selected_team_agent is not None:
                    assignee_id = str(selected_team_agent.agent_user_id)
                    if assignee_id not in candidate_assignee_ids:
                        candidate_assignee_ids.append(assignee_id)
                    max_open_tickets_by_assignee[assignee_id] = (
                        selected_team_agent.max_open_tickets
                    )

        profile_filters = (matched_policy.filters or {}).get("agent_profile") or {}

        if profile_filters:
            matched_agents = await self.agent_repo.list_matching_profiles(
                user_id=user_id,
                channels=profile_filters.get("channels"),
                skills=profile_filters.get("skills"),
                languages=profile_filters.get("languages"),
                available_only=profile_filters.get("available_only", True),
                active_only=profile_filters.get("active_only", True),
            )

            profile_candidate_ids = [
                str(agent.agent_user_id) for agent in matched_agents
            ]

            max_open_tickets_by_assignee = {
                str(agent.agent_user_id): agent.max_open_tickets
                for agent in matched_agents
            }

            if candidate_assignee_ids:
                candidate_assignee_ids = [
                    candidate_id
                    for candidate_id in candidate_assignee_ids
                    if candidate_id in set(profile_candidate_ids)
                ]
            else:
                candidate_assignee_ids = profile_candidate_ids

        selected_assignee = await self.selector.select(
            user_id=user_id,
            strategy=matched_policy.strategy,
            candidate_assignee_ids=candidate_assignee_ids,
            max_open_tickets_by_assignee=max_open_tickets_by_assignee,
        )

        if selected_assignee is None:
            return None

        assignment = await AssignmentService(
            db=self.db,
            user_id=user_id,
        ).assign(
            ticket_id=ticket.id,
            assigned_to=selected_assignee,
            meta={
                "routing_policy_id": str(matched_policy.id),
                "routing_policy_name": matched_policy.name,
                "candidate_team_ids": team_ids,
                "candidate_queue_ids": queue_ids,
            },
        )

        return {
            "policy_id": matched_policy.id,
            "ticket_id": ticket.id,
            "assigned_to": selected_assignee,
            "assignment_id": assignment.id if assignment else None,
        }
