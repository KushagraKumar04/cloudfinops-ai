import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.base import CamelModel


class InvitationCreateIn(CamelModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(owner|admin|member|viewer)$")


class InvitationOut(CamelModel):
    id: uuid.UUID
    email: str
    role: str
    status: str
    expires_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime
    invite_url: str | None = None
    invited_by_name: str | None = None


class InvitationListOut(CamelModel):
    items: list[InvitationOut]
    total: int


class InvitationPreview(CamelModel):
    email: str
    role: str
    tenant_name: str
    tenant_slug: str
    expires_at: datetime
    status: str


class InvitationAcceptIn(CamelModel):
    password: str | None = Field(default=None, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)


class OAuthProvider(CamelModel):
    id: str
    label: str
    enabled: bool