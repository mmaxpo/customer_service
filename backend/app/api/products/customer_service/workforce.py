from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/agents.py
# ============================================================
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.agents import (
    AgentCreate,
    AgentRead,
    AgentUpdate,
    AgentPresenceUpdate, AgentTimeOffCreate, AgentTimeOffRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
    get_customer_service_principal,
)
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.domains.customer_service.services.workforce.agents import (
    CustomerServiceAgentService,
)
from app.domains.customer_service.services.workforce.time_off import AgentTimeOffService
from app.domains.customer_service.realtime.publisher import CustomerServiceRealtimePublisher

agents_router = APIRouter(tags=["Customer Service Agents"])


@agents_router.patch("/agents/me/presence", response_model=AgentRead)
async def set_my_presence(
    payload: AgentPresenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    workspace_id = getattr(current_user, "workspace_id", current_user.id)
    actor_user_id = getattr(current_user, "actor_user_id", current_user.id)
    agent = await CustomerServiceAgentService(db).set_presence(
        workspace_id=workspace_id,
        agent_user_id=actor_user_id,
        status=payload.status,
    )
    await CustomerServiceRealtimePublisher().publish_agent_presence_changed(
        user_id=workspace_id, agent=agent
    )
    return agent


@agents_router.post("/agents/me/presence/activity", response_model=AgentRead)
async def record_my_presence_activity(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    workspace_id = getattr(current_user, "workspace_id", current_user.id)
    agent = await CustomerServiceAgentService(db).record_activity(
        workspace_id=workspace_id,
        agent_user_id=getattr(current_user, "actor_user_id", current_user.id),
    )
    return agent


@agents_router.post("/agents/{agent_id}/time-off", response_model=AgentTimeOffRead)
async def create_agent_time_off(
    agent_id: UUID, payload: AgentTimeOffCreate, db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    return await AgentTimeOffService(db).create(
        workspace_id=current_user.id, agent_id=agent_id,
        actor_user_id=getattr(current_user, "actor_user_id", current_user.id),
        starts_at=payload.starts_at, ends_at=payload.ends_at, reason=payload.reason,
    )


@agents_router.get("/agents/{agent_id}/time-off", response_model=list[AgentTimeOffRead])
async def list_agent_time_off(
    agent_id: UUID, db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    return await AgentTimeOffService(db).list(workspace_id=current_user.id, agent_id=agent_id)


@agents_router.delete("/agents/{agent_id}/time-off/{time_off_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_time_off(
    agent_id: UUID, time_off_id: UUID, db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    await AgentTimeOffService(db).delete(workspace_id=current_user.id, time_off_id=time_off_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@agents_router.post("/agents", response_model=AgentRead)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.agents.manage")),
):
    return await CustomerServiceAgentService(db).create(
        user_id=current_user.id,
        payload=payload,
    )


@agents_router.get("/agents", response_model=list[AgentRead])
async def list_agents(
    active_only: bool | None = Query(default=None),
    available_only: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.agents.manage")),
):
    return await CustomerServiceAgentService(db).list_for_user(
        user_id=current_user.id,
        active_only=active_only,
        available_only=available_only,
    )


@agents_router.get("/agents/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.agents.manage")),
):
    return await CustomerServiceAgentService(db).get(
        user_id=current_user.id,
        agent_id=agent_id,
    )


@agents_router.patch("/agents/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.agents.manage")),
):
    return await CustomerServiceAgentService(db).update(
        user_id=current_user.id,
        agent_id=agent_id,
        payload=payload,
    )


@agents_router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.agents.manage")),
):
    await CustomerServiceAgentService(db).delete(
        user_id=current_user.id,
        agent_id=agent_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/teams.py
# ============================================================


from fastapi import APIRouter, Depends, Query, status

from app.core.session import get_db
from app.domains.customer_service.schemas.teams import (
    TeamCreate,
    TeamDetail,
    TeamMemberAdd,
    TeamMemberRead,
    TeamRead,
    TeamUpdate,
)
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.domains.customer_service.services.workforce.teams import (
    CustomerServiceTeamService,
)

teams_router = APIRouter(tags=["Customer Service Teams"])


@teams_router.post("/teams", response_model=TeamRead)
async def create_team(
    payload: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    return await CustomerServiceTeamService(db).create(
        user_id=current_user.id,
        payload=payload,
    )


@teams_router.get("/teams", response_model=list[TeamRead])
async def list_teams(
    active_only: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    return await CustomerServiceTeamService(db).list_for_user(
        user_id=current_user.id,
        active_only=active_only,
    )


@teams_router.get("/teams/{team_id}", response_model=TeamDetail)
async def get_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    return await CustomerServiceTeamService(db).get_detail(
        user_id=current_user.id,
        team_id=team_id,
    )


@teams_router.patch("/teams/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    return await CustomerServiceTeamService(db).update(
        user_id=current_user.id,
        team_id=team_id,
        payload=payload,
    )


@teams_router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    await CustomerServiceTeamService(db).delete(
        user_id=current_user.id,
        team_id=team_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@teams_router.post("/teams/{team_id}/members", response_model=TeamMemberRead)
async def add_team_member(
    team_id: UUID,
    payload: TeamMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    return await CustomerServiceTeamService(db).add_member(
        user_id=current_user.id,
        team_id=team_id,
        agent_id=payload.agent_id,
    )


@teams_router.delete(
    "/teams/{team_id}/members/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_team_member(
    team_id: UUID,
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.teams.manage")),
):
    await CustomerServiceTeamService(db).remove_member(
        user_id=current_user.id,
        team_id=team_id,
        agent_id=agent_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/queues.py
# ============================================================


from fastapi import APIRouter, Depends, status

from app.core.session import get_db
from app.domains.customer_service.schemas.queues import (
    QueueCreate,
    QueueRead,
    QueueUpdate,
)
from app.domains.customer_service.services.workforce.queues import CustomerServiceQueueService

queues_router = APIRouter(tags=["Customer Service Queues"])


@queues_router.post("/queues", response_model=QueueRead)
async def create_queue(
    payload: QueueCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceQueueService(db).create(
        user_id=current_user.id, payload=payload
    )


@queues_router.get("/queues", response_model=list[QueueRead])
async def list_queues(
    active_only: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceQueueService(db).list_for_user(
        user_id=current_user.id,
        active_only=active_only,
    )


@queues_router.get("/queues/{queue_id}", response_model=QueueRead)
async def get_queue(
    queue_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceQueueService(db).get(
        user_id=current_user.id, queue_id=queue_id
    )


@queues_router.patch("/queues/{queue_id}", response_model=QueueRead)
async def update_queue(
    queue_id: UUID,
    payload: QueueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceQueueService(db).update(
        user_id=current_user.id,
        queue_id=queue_id,
        payload=payload,
    )


@queues_router.delete("/queues/{queue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_queue(
    queue_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await CustomerServiceQueueService(db).delete(
        user_id=current_user.id, queue_id=queue_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/routing_policies.py
# ============================================================


from fastapi import APIRouter, Depends, Query, status

from app.core.session import get_db
from app.domains.customer_service.schemas.routing_policies import (
    RoutingPolicyCreate,
    RoutingPolicyRead,
    RoutingPolicyUpdate,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.domains.customer_service.services.routing_policies import (
    CustomerServiceRoutingPolicyService,
)

routing_policies_router = APIRouter(tags=["Customer Service Routing Policies"])


@routing_policies_router.post("/routing-policies", response_model=RoutingPolicyRead)
async def create_routing_policy(
    payload: RoutingPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.routing.manage")),
):
    return await CustomerServiceRoutingPolicyService(db).create(
        user_id=current_user.id,
        payload=payload,
    )


@routing_policies_router.get(
    "/routing-policies", response_model=list[RoutingPolicyRead]
)
async def list_routing_policies(
    active_only: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.routing.manage")),
):
    return await CustomerServiceRoutingPolicyService(db).list_for_user(
        user_id=current_user.id,
        active_only=active_only,
    )


@routing_policies_router.get(
    "/routing-policies/{policy_id}", response_model=RoutingPolicyRead
)
async def get_routing_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.routing.manage")),
):
    return await CustomerServiceRoutingPolicyService(db).get(
        user_id=current_user.id,
        policy_id=policy_id,
    )


@routing_policies_router.patch(
    "/routing-policies/{policy_id}", response_model=RoutingPolicyRead
)
async def update_routing_policy(
    policy_id: UUID,
    payload: RoutingPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.routing.manage")),
):
    return await CustomerServiceRoutingPolicyService(db).update(
        user_id=current_user.id,
        policy_id=policy_id,
        payload=payload,
    )


@routing_policies_router.delete(
    "/routing-policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_routing_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.routing.manage")),
):
    await CustomerServiceRoutingPolicyService(db).delete(
        user_id=current_user.id,
        policy_id=policy_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/sla.py
# ============================================================

from fastapi import APIRouter, Depends, Query

from app.core.session import get_db
from app.domains.customer_service.schemas.sla import (
    SLAPolicyCreate,
    SLAPolicyRead,
    SLAViolationRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.domains.customer_service.services.sla import SLAService

sla_router = APIRouter(
    prefix="/sla",
    tags=["Customer Service - SLA"],
)


@sla_router.post("/policies", response_model=SLAPolicyRead)
async def create_sla_policy(
    payload: SLAPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.sla.manage")),
):
    return await SLAService(db).create_policy(
        user_id=current_user.id,
        payload=payload,
    )


@sla_router.get("/policies", response_model=list[SLAPolicyRead])
async def list_sla_policies(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.sla.read")),
):
    return await SLAService(db).list_policies(user_id=current_user.id)


@sla_router.get("/violations", response_model=list[SLAViolationRead])
async def list_sla_violations(
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.sla.read")),
):
    return await SLAService(db).list_violations(
        user_id=current_user.id,
        status=status,
    )


@sla_router.post("/check", response_model=list[SLAViolationRead])
async def check_sla_breaches(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.sla.manage")),
):
    return await SLAService(db).check_breaches(
        user_id=current_user.id,
    )


@sla_router.post("/check-risk", response_model=list[SLAViolationRead])
async def check_sla_risk(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.sla.manage")),
):
    return await SLAService(db).check_at_risk(user_id=current_user.id)


__all__ = [
    "agents_router",
    "teams_router",
    "queues_router",
    "routing_policies_router",
    "sla_router",
]
