import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional


class DocumentBase(BaseModel):
    title: str = Field(..., examples=["README.md"])
    content: str | None = None

    model_config = {"from_attributes": True}


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

    model_config = {"from_attributes": True}


class TokenData(BaseModel):
    email: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    terms_accepted: bool
    terms_version: str
    privacy_accepted: bool
    privacy_version: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    email_verified_at: datetime.datetime | None = None

    model_config = {"from_attributes": True}


class UserInDB(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    email_verified_at: datetime.datetime | None = None
    hashed_password: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ThreadCreate(BaseModel):
    title: Optional[str] = None


class ThreadRead(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    created_at: datetime.datetime
    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    role: str
    content: str
    thread_id: Optional[str] = None


class MessageRead(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    role: str
    content: str
    created_at: datetime.datetime
    model_config = {"from_attributes": True}


class DocSummary(BaseModel):
    doc_id: str
    filename: str | None = None
    source: str | None = None
    mime_type: str | None = None
    chunks: int = Field(..., description="How many chunks were stored for this doc")


class DeleteDocsBody(BaseModel):
    doc_ids: list[str] | None = None
    filenames: list[str] | None = None
