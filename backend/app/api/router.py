from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.send_email import router as send_email_router
from app.api.products.customer_service.router import router as customer_service_router
from app.api.platform import (
    events_router,
    jobs_router,
    schedules_router,
    webhooks_router,
)
from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.knowledge import router as knowledge_router
from app.api.tools import router as tools_router
from app.api.tcos import router as tcos_router
from app.api.capabilities import router as capabilities_router
from app.api.workspaces import router as workspaces_router
from app.api.workflows import router as workflows_router
from app.api.workflow_operations import (
    workflow_diff_router,
    workflow_evaluations_router,
    workflow_metrics_router,
    workflow_quality_router,
    workflow_snapshots_router,
    workflow_timeline_router,
    workflow_versions_router,
    workflow_waits_router,
)


api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(workflows_router)
api_router.include_router(knowledge_router)
api_router.include_router(agents_router)
api_router.include_router(tools_router)
api_router.include_router(tcos_router)
api_router.include_router(capabilities_router)
api_router.include_router(workspaces_router)

api_router.include_router(customer_service_router)

api_router.include_router(jobs_router)
api_router.include_router(schedules_router)
api_router.include_router(webhooks_router)
api_router.include_router(events_router)

api_router.include_router(workflow_waits_router)
api_router.include_router(workflow_snapshots_router)
api_router.include_router(workflow_timeline_router)
api_router.include_router(workflow_diff_router)
api_router.include_router(workflow_evaluations_router)
api_router.include_router(workflow_versions_router)
api_router.include_router(workflow_metrics_router)
api_router.include_router(workflow_quality_router)

api_router.include_router(send_email_router)
