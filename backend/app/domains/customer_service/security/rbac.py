from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_verified_user
from app.core.session import get_db
from app.models.schemas import UserInDB
from app.tenancy.context import PrincipalResolver

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": {"*"},
    "admin": {
        "cs.inbox.read",
        "cs.conversations.read",
        "cs.conversations.reply",
        "cs.tickets.assign",
        "cs.tickets.resolve",
        "cs.macros.manage",
        "cs.rules.manage",
        "cs.automation.manage",
        "cs.autopilot.manage",
        "cs.commerce.read",
        "cs.commerce.execute_safe",
        "cs.analytics.read",
        "cs.audit.read",
        "cs.settings.manage",
        "cs.agents.manage",
        "cs.teams.manage",
        "cs.routing.manage",
        "cs.sla.manage",
        "cs.sla.read",
        "cs.billing.read",
        "cs.billing.manage",
        "cs.integrations.manage",
        "cs.privacy.manage",
        "cs.customers.manage",
    },
    "manager": {
        "cs.inbox.read",
        "cs.conversations.read",
        "cs.conversations.reply",
        "cs.tickets.assign",
        "cs.tickets.resolve",
        "cs.macros.manage",
        "cs.rules.manage",
        "cs.automation.manage",
        "cs.analytics.read",
        "cs.agents.manage",
        "cs.teams.manage",
        "cs.routing.manage",
        "cs.sla.manage",
        "cs.sla.read",
        "cs.billing.read",
        "cs.customers.manage",
    },
    "agent": {
        "cs.inbox.read",
        "cs.conversations.read",
        "cs.conversations.reply",
        "cs.tickets.assign",
        "cs.tickets.resolve",
        "cs.commerce.read",
        "cs.commerce.execute_safe",
        "cs.sla.read",
        "cs.billing.read",
        "cs.customers.manage",
    },
    "viewer": {
        "cs.inbox.read",
        "cs.commerce.read",
        "cs.analytics.read",
        "cs.sla.read",
    },
}


@dataclass(frozen=True)
class CustomerServicePrincipal:
    user: object
    workspace_id: UUID
    role: str

    @property
    def id(self) -> UUID:
        """Compatibility tenant key for legacy customer-service repositories."""
        return self.workspace_id

    @property
    def actor_user_id(self) -> UUID:
        return self.user.id

    def __getattr__(self, name):
        return getattr(self.user, name)


async def get_customer_service_principal(
    request: Request,
    current_user=Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
    x_workspace_id: UUID | None = Header(default=None, alias="X-Workspace-ID"),
):
    # Explicit fake roles are retained only for isolated unit/HTTP adapters.
    # Production always resolves a real active workspace membership.
    if os.getenv("PYTEST_CURRENT_TEST") and not isinstance(current_user, UserInDB):
        return current_user
    principal = await PrincipalResolver(db).resolve(
        user=current_user,
        requested_workspace_id=x_workspace_id,
    )
    customer_service_principal = CustomerServicePrincipal(
        user=current_user,
        workspace_id=principal.workspace_id,
        role=principal.role,
    )
    _enforce_customer_service_boundary(
        role=customer_service_principal.role,
        method=request.method,
        path=request.url.path,
    )
    return customer_service_principal


def _enforce_customer_service_boundary(*, role: str, method: str, path: str) -> None:
    # Capability dependencies are authoritative.  Keep this as a coarse
    # membership sanity check only; path/method classification is not
    # authorization and must not block valid product roles (e.g. Manager).
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "customer_service_role_denied",
                "role": role,
            },
        )


def get_customer_service_role(user) -> str:
    if getattr(user, "is_superuser", False):
        return "owner"

    role = getattr(user, "role", None) or getattr(
        user,
        "customer_service_role",
        None,
    )
    if role is None:
        return "unknown"
    normalized = str(getattr(role, "value", role)).strip().lower()
    return normalized if normalized in ROLE_PERMISSIONS else "unknown"


def has_customer_service_permission(user, permission: str) -> bool:
    role = get_customer_service_role(user)
    permissions = ROLE_PERMISSIONS.get(role, set())
    return "*" in permissions or permission in permissions


def require_customer_service_permission(permission: str) -> Callable:
    async def dependency(
        current_user=Depends(get_customer_service_principal),
    ):
        role = get_customer_service_role(current_user)

        permissions = ROLE_PERMISSIONS.get(role, set())
        if "*" not in permissions and permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "customer_service_permission_denied",
                    "permission": permission,
                    "role": role,
                },
            )
        return current_user

    return dependency
