from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.tenancy.context import PrincipalResolver


@dataclass
class FakeUser:
    id: UUID


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    async def list_for_user(self, *, user_id):
        return self.rows


@dataclass
class FakeWorkspace:
    id: UUID
    kind: str


@dataclass
class FakeMembership:
    id: UUID
    role: str


@pytest.mark.asyncio
async def test_principal_defaults_to_personal_and_honors_authorized_header():
    user = FakeUser(uuid4())
    personal = (
        FakeWorkspace(uuid4(), "personal"),
        FakeMembership(uuid4(), "owner"),
    )
    merchant = (
        FakeWorkspace(uuid4(), "organization"),
        FakeMembership(uuid4(), "agent"),
    )
    resolver = PrincipalResolver(db=None)
    resolver.repo = FakeRepository([merchant, personal])

    default = await resolver.resolve(user=user, requested_workspace_id=None)
    assert default.workspace_id == personal[0].id
    assert default.selection_source == "personal_default"

    selected = await resolver.resolve(
        user=user,
        requested_workspace_id=merchant[0].id,
    )
    assert selected.workspace_id == merchant[0].id
    assert selected.role == "agent"
    assert selected.selection_source == "header"


@pytest.mark.asyncio
async def test_principal_rejects_an_unauthorized_workspace_selection():
    user = FakeUser(uuid4())
    authorized = (
        FakeWorkspace(uuid4(), "personal"),
        FakeMembership(uuid4(), "owner"),
    )
    resolver = PrincipalResolver(db=None)
    resolver.repo = FakeRepository([authorized])

    with pytest.raises(HTTPException) as exc_info:
        await resolver.resolve(user=user, requested_workspace_id=uuid4())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {"code": "workspace_membership_required"}


@pytest.mark.asyncio
async def test_principal_opens_the_remembered_workspace_when_still_a_member():
    merchant = (
        FakeWorkspace(uuid4(), "organization"),
        FakeMembership(uuid4(), "agent"),
    )
    personal = (
        FakeWorkspace(uuid4(), "personal"),
        FakeMembership(uuid4(), "owner"),
    )
    resolver = PrincipalResolver(db=None)
    resolver.repo = FakeRepository([merchant, personal])

    user = FakeUser(uuid4())
    user.active_workspace_id = merchant[0].id
    remembered = await resolver.resolve(user=user, requested_workspace_id=None)
    assert remembered.workspace_id == merchant[0].id
    assert remembered.role == "agent"
    assert remembered.selection_source == "remembered"

    # A workspace the user no longer belongs to is ignored.
    user.active_workspace_id = uuid4()
    fallback = await resolver.resolve(user=user, requested_workspace_id=None)
    assert fallback.workspace_id == personal[0].id
    assert fallback.selection_source == "personal_default"
