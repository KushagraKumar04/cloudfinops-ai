import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.base import CamelModel


class RegisterIn(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=200)
    organization_name: str = Field(default="", max_length=200)


class LoginIn(CamelModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(CamelModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class TenantOut(CamelModel):
    id: uuid.UUID
    slug: str
    name: str
    role: str


class TokenOut(CamelModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    tenant: TenantOut | None = None