import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


class TeamMemberUser(CamelModel):
    id: uuid.UUID
    email: str
    full_name: str


class TeamMemberOut(CamelModel):
    id: uuid.UUID
    user: TeamMemberUser
    role: str
    created_at: datetime


class TeamListOut(CamelModel):
    items: list[TeamMemberOut]
    total: int
    current_role: str


class TeamMemberUpdateIn(CamelModel):
    role: str = Field(pattern="^(owner|admin|member|viewer)$")