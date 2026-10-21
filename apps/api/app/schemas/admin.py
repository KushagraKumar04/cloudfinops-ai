import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel


class TenantSummary(CamelModel):
    id: uuid.UUID
    slug: str
    name: str
    created_at: datetime
    user_count: int = 0
    cloud_account_count: int = 0
    resource_count: int = 0
    recommendation_count: int = 0
    cost_record_count: int = 0
    audit_event_count: int = 0


class TenantListOut(CamelModel):
    items: list[TenantSummary]
    total: int


class TenantDetail(TenantSummary):
    members: list["AdminMember"] = Field(default_factory=list)
    cloud_accounts: list["AdminCloudAccount"] = Field(default_factory=list)
    recent_recommendations: int = 0


class AdminMember(CamelModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    joined_at: datetime
    last_login_at: datetime | None = None


class AdminCloudAccount(CamelModel):
    id: uuid.UUID
    name: str
    provider: str
    environment: str
    status: str
    resource_count: int = 0
    monthly_spend: float = 0
    disabled: bool = False


class AdminUserRow(CamelModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    tenant_count: int = 0


class AdminUserListOut(CamelModel):
    items: list[AdminUserRow]
    total: int


class AdminUserUpdate(CamelModel):
    is_active: bool | None = None
    is_superuser: bool | None = None


class PlatformStats(CamelModel):
    tenant_count: int = 0
    user_count: int = 0
    active_user_count: int = 0
    cloud_account_count: int = 0
    resource_count: int = 0
    recommendation_count: int = 0
    cost_record_count: int = 0
    audit_event_count: int = 0
    total_monthly_spend: float = 0
    breakdown: dict[str, Any] = Field(default_factory=dict)


TenantDetail.model_rebuild()