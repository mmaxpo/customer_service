from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.tenancy.working_calendar import normalize_working_calendar, validate_timezone


_LOCALE_PATTERN = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"


class MembershipStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    logo_url: str | None = Field(default=None, max_length=2048)
    support_email: EmailStr | None = None
    default_sender_name: str | None = Field(default=None, max_length=255)
    default_sender_email: EmailStr | None = None
    default_locale: str = Field(default="en", max_length=35)
    timezone: str = Field(default="UTC", max_length=100)
    business_hours: dict | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return validate_timezone(value)

    @field_validator("business_hours")
    @classmethod
    def validate_business_hours(cls, value: dict | None) -> dict:
        return normalize_working_calendar(value)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("workspace name cannot be blank")
        return normalized

    @field_validator("default_sender_name")
    @classmethod
    def normalize_sender_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("default sender name cannot be blank")
        return normalized

    @field_validator("default_locale")
    @classmethod
    def normalize_locale(cls, value: str) -> str:
        normalized = value.strip()
        if not _LOCALE_PATTERN.fullmatch(normalized):
            raise ValueError("default locale must be a valid locale tag")
        return normalized


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    logo_url: str | None = Field(default=None, max_length=2048)
    business_name: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=100)
    business_hours: dict | None = None
    support_email: EmailStr | None = None
    default_sender_name: str | None = Field(default=None, max_length=255)
    default_sender_email: EmailStr | None = None
    default_locale: str | None = Field(default=None, max_length=35)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("workspace name cannot be blank")
        return normalized

    @field_validator("default_sender_name")
    @classmethod
    def normalize_sender_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("default sender name cannot be blank")
        return normalized

    @field_validator("default_locale")
    @classmethod
    def normalize_locale(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not _LOCALE_PATTERN.fullmatch(normalized):
            raise ValueError("default locale must be a valid locale tag")
        return normalized

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        return validate_timezone(value) if value is not None else None

    @field_validator("business_hours")
    @classmethod
    def validate_business_hours(cls, value: dict | None) -> dict | None:
        return normalize_working_calendar(value) if value is not None else None

    @model_validator(mode="after")
    def prevent_calendar_fields_from_being_cleared(self):
        if "timezone" in self.model_fields_set and self.timezone is None:
            raise ValueError("workspace timezone cannot be null")
        if "business_hours" in self.model_fields_set and self.business_hours is None:
            raise ValueError("workspace business_hours cannot be null")
        return self


class WorkspaceRead(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: str | None = None
    support_email: EmailStr | None = None
    default_sender_name: str | None = None
    default_sender_email: EmailStr | None = None
    default_locale: str
    kind: str
    status: str
    deletion_requested_at: datetime | None = None
    deletion_scheduled_for: datetime | None = None
    business_name: str | None = None
    timezone: str
    business_hours: dict
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    role: WorkspaceRole | None = None

    model_config = {"from_attributes": True}


class WorkspaceDeletionRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=100)


class WorkspaceDeletionRead(BaseModel):
    workspace_id: UUID
    status: str
    deletion_requested_at: datetime | None = None
    deletion_scheduled_for: datetime | None = None
    can_cancel: bool


class WorkspaceMetadataRead(BaseModel):
    workspace_id: UUID
    created_at: datetime
    plan: str


class WorkspaceSettingsAuditLogRead(BaseModel):
    id: UUID
    workspace_id: UUID
    actor_user_id: UUID
    action: str
    changes: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceMembershipRead(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    status: MembershipStatus
    joined_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceMembershipUpdate(BaseModel):
    role: WorkspaceRole | None = None
    status: MembershipStatus | None = None


class WorkspaceOwnershipTransfer(BaseModel):
    new_owner_user_id: UUID


DEFAULT_INVITATION_LIFETIME_HOURS = 24 * 7


class WorkspaceInvitationCreate(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.AGENT
    expires_in_hours: int = Field(
        default=DEFAULT_INVITATION_LIFETIME_HOURS, ge=1, le=24 * 30
    )

    @field_validator("role")
    @classmethod
    def owner_cannot_be_invited(cls, value: WorkspaceRole) -> WorkspaceRole:
        if value in {WorkspaceRole.OWNER, WorkspaceRole.VIEWER}:
            raise ValueError("owner and legacy viewer roles are not assignable for V1 invitations")
        return value


class WorkspaceInvitationRead(BaseModel):
    id: UUID
    workspace_id: UUID
    email: EmailStr
    role: WorkspaceRole
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceInvitationAccept(BaseModel):
    token: str = Field(min_length=32, max_length=512)


class TeamRosterEntry(BaseModel):
    id: UUID
    user_id: UUID | None = None
    invitation_id: UUID | None = None
    email: EmailStr
    display_name: str | None = None
    role: WorkspaceRole
    state: str
    invited_at: datetime
    joined_at: datetime | None = None


__all__ = [
    "DEFAULT_INVITATION_LIFETIME_HOURS",
    "MembershipStatus",
    "TeamRosterEntry",
    "WorkspaceCreate",
    "WorkspaceDeletionRead",
    "WorkspaceDeletionRequest",
    "WorkspaceInvitationAccept",
    "WorkspaceInvitationCreate",
    "WorkspaceInvitationRead",
    "WorkspaceMembershipRead",
    "WorkspaceMembershipUpdate",
    "WorkspaceOwnershipTransfer",
    "WorkspaceMetadataRead",
    "WorkspaceRead",
    "WorkspaceRole",
    "WorkspaceSettingsAuditLogRead",
    "WorkspaceUpdate",
]
