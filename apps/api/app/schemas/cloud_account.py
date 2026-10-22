import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class SyncCoverage(CamelModel):
    enabled: bool = False
    last_sync_at: datetime | None = None


class CloudAccountOut(CamelModel):
    id: uuid.UUID
    provider: str
    name: str
    identifier: str = Field(validation_alias="account_identifier")
    environment: str
    status: str

    role_arn: str | None = None
    subscription_id: str | None = None
    tenant_id: str | None = Field(default=None, validation_alias="tenant_external_id")

    regions: list[str] = Field(default_factory=list)
    read_only: bool = True
    execution_role_configured: bool = False
    disabled: bool = False

    created_at: datetime
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_message: str | None = None

    sync_phase: str | None = None
    sync_progress_pct: int = 0
    sync_started_at: datetime | None = None
    sync_completed_at: datetime | None = None
    sync_error_count: int = 0

    coverage: dict[str, SyncCoverage] = Field(default_factory=dict)
    resource_count: int = 0
    monthly_spend: float = 0
    currency: str = "USD"

    @field_validator("monthly_spend", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)

    @field_validator("disabled", mode="before")
    @classmethod
    def coerce_disabled(cls, v, info):
        data = info.data
        return data.get("disabled_at") is not None if v is None else bool(v)


class SyncResponse(CamelModel):
    id: uuid.UUID
    status: str


class ValidateResponse(CamelModel):
    id: uuid.UUID
    ok: bool
    message: str