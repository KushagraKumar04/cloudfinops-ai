import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class ResourceOut(CamelModel):
    id: uuid.UUID
    provider: str
    account_id: uuid.UUID = Field(validation_alias="cloud_account_id")
    account_name: str = ""
    cloud_id: str
    name: str
    type: str
    service: str
    region: str
    environment: str
    status: str
    application: str
    owner: str
    tags: list[dict[str, str]] = Field(default_factory=list)
    created_at: datetime
    monthly_cost: float = 0
    currency: str = "USD"
    utilization: dict[str, Any] = Field(default_factory=dict)
    series: dict[str, list[float]] = Field(default_factory=dict)
    metric_coverage: float = 0

    @field_validator("monthly_cost", "metric_coverage", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)


class EnvironmentAggregate(CamelModel):
    count: int
    cost: float


class ResourceAggregates(CamelModel):
    total_monthly_cost: float
    by_environment: dict[str, EnvironmentAggregate]
    by_provider: dict[str, EnvironmentAggregate]


class ResourceListOut(CamelModel):
    items: list[ResourceOut]
    total: int
    page: int
    page_size: int
    aggregates: ResourceAggregates